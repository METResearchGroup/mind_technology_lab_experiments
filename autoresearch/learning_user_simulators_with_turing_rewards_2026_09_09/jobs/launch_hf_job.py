#!/usr/bin/env python3
"""Submit the Qwen3-8B Turing-RL UV script to Hugging Face Jobs."""

from __future__ import annotations

import json
import os
from pathlib import Path

from huggingface_hub import HfApi

SCRIPT = Path(__file__).resolve().parent / "train_qwen3_8b_turing_rl.py"
DASHBOARD_JSON = (
    Path(__file__).resolve().parent.parent / "dashboard" / "data" / "hf_job.json"
)
RESULTS_JSON = Path(__file__).resolve().parent.parent / "results" / "hf_job.json"


def _secret(name: str, fallback: str | None = None) -> str | None:
    value = os.environ.get(name) or (os.environ.get(fallback) if fallback else None)
    return value or None


def main() -> None:
    token = _secret("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is missing")
    if not SCRIPT.is_file():
        raise SystemExit(f"missing script: {SCRIPT}")

    secrets: dict[str, str] = {"HF_TOKEN": token}
    openai_key = _secret("OPENAI_API_KEY")
    if openai_key:
        secrets["OPENAI_API_KEY"] = openai_key
    wandb_key = _secret("WANDB_API_KEY")
    if wandb_key:
        secrets["WANDB_API_KEY"] = wandb_key
    aws_key = _secret("AWS_ACCESS_KEY_ID") or _secret("LAB_AWS_ACCESS_KEY_ID")
    aws_secret = (
        _secret("AWS_SECRET_ACCESS_KEY")
        or _secret("AWS_ACCESS_KEY_SECRET")
        or _secret("LAB_AWS_ACCESS_KEY_SECRET")
    )
    if aws_key and aws_secret:
        secrets["AWS_ACCESS_KEY_ID"] = aws_key
        secrets["AWS_SECRET_ACCESS_KEY"] = aws_secret

    api = HfApi(token=token)
    who = api.whoami()
    username = who["name"] if isinstance(who, dict) else "mtorres98"
    print(f"submitting as {username}", flush=True)
    print(f"script={SCRIPT}", flush=True)
    print(f"secrets={sorted(secrets)}", flush=True)

    job = api.run_uv_job(
        str(SCRIPT),
        flavor="a100-large",
        timeout="3h",
        name="turing-rl-qwen3-8b",
        secrets=secrets,
        env={
            "TRACKIO_PROJECT": "turing-rl-qwen3-8b",
            "TURING_JUDGE_MODEL": "gpt-4o-mini",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        },
    )
    payload = {
        "job_id": job.id,
        "job_url": job.url,
        "owner": username,
        "flavor": "a100-large",
        "timeout": "3h",
        "estimated_cost_usd": "up to ~7.50 at $2.50/hr if the 3h timeout is used",
        "base_model": "Qwen/Qwen3-8B",
        "sft_repo": f"{username}/turing-rl-qwen3-8b-sft",
        "grpo_repo": f"{username}/turing-rl-qwen3-8b-grpo",
        "trackio_project": "turing-rl-qwen3-8b",
        "trackio_url": f"https://huggingface.co/spaces/{username}/trackio",
        "paper_judge": "Qwen/Qwen3.5-397B-A17B via OpenRouter",
        "job_judge": "gpt-4o-mini via OpenAI",
        "job_judge_reason": "OPENROUTER_API_KEY is missing in this environment",
        "scale_note": (
            "LoRA SFT (24 steps) then GRPO (8 steps, G=4, max new tokens 256). "
            "This is a real Qwen3-8B run, not the paper's 1680 GPU-hour training."
        ),
        "missing_keys": [
            key
            for key in (
                "OPENROUTER_API_KEY",
                "LAB_AWS_ACCESS_KEY_ID",
                "LAB_AWS_ACCESS_KEY_SECRET",
                "VERCEL_TOKEN",
            )
            if not os.environ.get(key)
        ],
        "status": getattr(getattr(job, "status", None), "stage", None) or "RUNNING",
    }
    text = json.dumps(payload, indent=2)
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(text + "\n", encoding="utf-8")
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.write_text(text + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2), flush=True)


if __name__ == "__main__":
    main()
