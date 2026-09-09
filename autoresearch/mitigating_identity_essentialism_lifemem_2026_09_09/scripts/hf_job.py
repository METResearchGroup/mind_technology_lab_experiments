#!/usr/bin/env python3
"""GPU LifeMem run on Qwen/Qwen3.5-4B. Intended for Hugging Face Jobs."""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "numpy>=2.0.0",
#   "peft>=0.14.0",
#   "torch>=2.4.0",
#   "transformers>=4.51.0",
#   "huggingface_hub>=0.30.0",
# ]
# ///

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from huggingface_hub import HfApi, login
from lifemem.config import LifeMemConfig
from lifemem.experiment import run_suite, write_json
from lifemem.lora_memory import lora_config_dict


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if token:
        login(token=token)
    config = LifeMemConfig()
    results = run_suite(config, n_agents=16, n_waves=6, events_per_wave=8)
    results["lora"] = lora_config_dict(config)
    results["backbone"] = config.model_name
    out = Path("lifemem_replication_results.json")
    write_json(results, out)
    username = os.environ.get("HF_USERNAME")
    if token:
        api = HfApi(token=token)
        if not username:
            username = api.whoami()["name"]
        repo_id = f"{username}/lifemem-replication-2026-09-09"
        api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=False)
        api.upload_file(
            path_or_fileobj=str(out),
            path_in_repo="replication_results.json",
            repo_id=repo_id,
            repo_type="dataset",
        )
        print(
            json.dumps({"hub": f"https://huggingface.co/datasets/{repo_id}"}, indent=2)
        )
    print(json.dumps({k: v["kl"] for k, v in results["methods"].items()}, indent=2))


if __name__ == "__main__":
    main()
