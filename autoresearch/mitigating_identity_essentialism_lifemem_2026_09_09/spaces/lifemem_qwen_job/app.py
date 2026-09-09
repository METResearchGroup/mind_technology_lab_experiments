"""ZeroGPU runner for the LifeMem Qwen/Qwen3.5-4B suite."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import gradio as gr
import spaces
from huggingface_hub import login, snapshot_download


def _load_package() -> Path:
    token = os.environ.get("HF_TOKEN")
    if token:
        login(token=token)
    snap = Path(
        snapshot_download(
            repo_id=os.environ.get(
                "LIFEMEM_SRC_REPO", "mtorres98/lifemem-replication-src"
            ),
            repo_type="dataset",
            token=token,
        )
    )
    if str(snap) not in sys.path:
        sys.path.insert(0, str(snap))
    return snap


@spaces.GPU(duration=240)
def run_qwen_suite() -> str:
    import torch

    _load_package()
    from lifemem.artifacts import push_json
    from lifemem.config import LifeMemConfig
    from lifemem.experiment import run_suite
    from lifemem.lora_memory import lora_config_dict

    if not torch.cuda.is_available():
        return json.dumps({"error": "CUDA not attached inside @spaces.GPU"})
    config = LifeMemConfig()
    results = run_suite(
        config,
        n_agents=int(os.environ.get("LIFEMEM_N_AGENTS", "2")),
        n_waves=int(os.environ.get("LIFEMEM_N_WAVES", "3")),
        events_per_wave=int(os.environ.get("LIFEMEM_EVENTS_PER_WAVE", "6")),
        backend="llm",
    )
    results["lora"] = lora_config_dict(config)
    results["backbone"] = config.model_name
    results["device"] = torch.cuda.get_device_name(0)
    results["hardware"] = "zerogpu"
    urls = push_json(results, "gpu_results.json", Path("gpu_results.json"))
    payload = {
        "device": results["device"],
        "urls": urls,
        "kl": {name: row["kl"] for name, row in results["methods"].items()},
        "n_agents": results["config"]["n_agents"],
        "n_waves": results["config"]["n_waves"],
    }
    return json.dumps(payload, indent=2)


with gr.Blocks(title="LifeMem Qwen GPU") as demo:
    gr.Markdown(
        "Runs the LifeMem suite on **Qwen/Qwen3.5-4B** with per-agent LoRA. "
        "Hugging Face Jobs is the intended path; this Space is the ZeroGPU fallback."
    )
    out = gr.Code(label="GPU result", language="json")
    gr.Button("Run Qwen LifeMem").click(run_qwen_suite, outputs=out)

if __name__ == "__main__":
    demo.launch()
