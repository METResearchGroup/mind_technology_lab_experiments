#!/usr/bin/env python3
"""GPU LifeMem run on Qwen/Qwen3.5-4B. Intended for Hugging Face Jobs.

`hf jobs uv run` only uploads this file, so the job downloads `lifemem/` from
the source dataset when it is not already on PYTHONPATH.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "accelerate>=1.0.0",
#   "boto3>=1.35.0",
#   "huggingface_hub>=0.30.0",
#   "numpy>=2.0.0",
#   "peft>=0.17.0",
#   "pillow>=10.0.0",
#   "safetensors>=0.4.0",
#   "torch>=2.6.0",
#   "transformers>=5.0.0",
# ]
# ///

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _ensure_package() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        Path(os.environ["LIFEMEM_SRC_MOUNT"])
        if os.environ.get("LIFEMEM_SRC_MOUNT")
        else None,
        here.parents[1] if here.parent.name == "scripts" else here.parent,
        Path("/src"),
    ]
    for local in candidates:
        if local is None:
            continue
        if (local / "lifemem" / "config.py").exists():
            if str(local) not in sys.path:
                sys.path.insert(0, str(local))
            return local
    from huggingface_hub import snapshot_download

    repo = os.environ.get("LIFEMEM_SRC_REPO", "mtorres98/lifemem-replication-src")
    snap = Path(
        snapshot_download(
            repo_id=repo,
            repo_type="dataset",
            token=os.environ.get("HF_TOKEN"),
        )
    )
    if str(snap) not in sys.path:
        sys.path.insert(0, str(snap))
    return snap


ROOT = _ensure_package()

from huggingface_hub import login
from lifemem.artifacts import push_json
from lifemem.config import LifeMemConfig
from lifemem.experiment import run_suite
from lifemem.lora_memory import lora_config_dict


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if token:
        login(token=token)
    try:
        import torch
    except ImportError as exc:
        raise SystemExit("torch is required for the GPU backend") from exc
    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is required for the Qwen LifeMem job; got CPU-only torch"
        )
    print(json.dumps({"cuda": torch.cuda.get_device_name(0), "root": str(ROOT)}))
    config = LifeMemConfig(
        model_name=os.environ.get("LIFEMEM_MODEL", "Qwen/Qwen3.5-4B")
    )
    n_agents = _int_env("LIFEMEM_N_AGENTS", 8)
    n_waves = _int_env("LIFEMEM_N_WAVES", 6)
    events_per_wave = _int_env("LIFEMEM_EVENTS_PER_WAVE", 8)
    results = run_suite(
        config,
        n_agents=n_agents,
        n_waves=n_waves,
        events_per_wave=events_per_wave,
        backend="llm",
    )
    results["lora"] = lora_config_dict(config)
    results["backbone"] = config.model_name
    results["device"] = torch.cuda.get_device_name(0)
    out = Path(os.environ.get("LIFEMEM_OUT", "gpu_results.json"))
    urls = push_json(results, "gpu_results.json", out)
    print(json.dumps({"urls": urls}, indent=2))
    print(json.dumps({k: v["kl"] for k, v in results["methods"].items()}, indent=2))


if __name__ == "__main__":
    main()
