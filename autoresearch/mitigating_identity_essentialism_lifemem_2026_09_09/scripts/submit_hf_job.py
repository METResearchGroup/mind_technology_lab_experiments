#!/usr/bin/env python3
"""Upload LifeMem sources and submit a Hugging Face Jobs GPU run."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from huggingface_hub import HfApi, Volume, login
from lifemem.artifacts import DEFAULT_RESULTS_REPO, DEFAULT_SRC_REPO, aws_credentials

FLAVOR = os.environ.get("LIFEMEM_FLAVOR", "a10g-small")
TIMEOUT = os.environ.get("LIFEMEM_TIMEOUT", "3h")
N_AGENTS = os.environ.get("LIFEMEM_N_AGENTS", "8")
N_WAVES = os.environ.get("LIFEMEM_N_WAVES", "6")


def upload_source(api: HfApi, username: str) -> str:
    repo_id = os.environ.get("LIFEMEM_SRC_REPO", DEFAULT_SRC_REPO)
    if repo_id.startswith("mtorres98/") and username != "mtorres98":
        repo_id = f"{username}/lifemem-replication-src"
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=repo_id,
        repo_type="dataset",
        allow_patterns=[
            "lifemem/*.py",
            "scripts/hf_job.py",
            "scripts/gpu_bootstrap.sh",
            "pyproject.toml",
            "README.md",
        ],
        commit_message="LifeMem Qwen GPU job sources",
    )
    return repo_id


def submit(api: HfApi, src_repo: str) -> dict:
    key, secret = aws_credentials()
    secrets = {"HF_TOKEN": os.environ["HF_TOKEN"]}
    if key and secret:
        secrets["AWS_ACCESS_KEY_ID"] = key
        secrets["AWS_SECRET_ACCESS_KEY"] = secret
    env = {
        "LIFEMEM_SRC_REPO": src_repo,
        "LIFEMEM_SRC_MOUNT": "/src",
        "LIFEMEM_RESULTS_REPO": os.environ.get(
            "LIFEMEM_RESULTS_REPO", DEFAULT_RESULTS_REPO
        ),
        "LIFEMEM_N_AGENTS": N_AGENTS,
        "LIFEMEM_N_WAVES": N_WAVES,
        "LIFEMEM_EVENTS_PER_WAVE": os.environ.get("LIFEMEM_EVENTS_PER_WAVE", "8"),
        "LIFEMEM_MODEL": os.environ.get("LIFEMEM_MODEL", "Qwen/Qwen3.5-4B"),
        "LIFEMEM_HARDWARE": "huggingface-jobs",
        "LIFEMEM_PROGRESS": "1",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    }
    namespace = os.environ.get("LIFEMEM_JOBS_NAMESPACE")
    job = api.run_job(
        image="pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel",
        command=[
            "bash",
            "-lc",
            "pip install -q 'transformers>=5.0.0' peft accelerate pillow "
            "huggingface_hub boto3 torchvision numpy safetensors hf_transfer && "
            "python /src/scripts/hf_job.py",
        ],
        flavor=FLAVOR,
        timeout=TIMEOUT,
        secrets=secrets,
        env=env,
        name="lifemem-qwen-4b",
        volumes=[Volume(type="dataset", source=src_repo, mount_path="/src")],
        namespace=namespace,
    )
    return {
        "status": "submitted",
        "id": job.id,
        "url": job.url,
        "flavor": FLAVOR,
        "timeout": TIMEOUT,
        "src_repo": src_repo,
        "n_agents": int(N_AGENTS),
        "n_waves": int(N_WAVES),
        "model": env["LIFEMEM_MODEL"],
    }


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required to submit Hugging Face Jobs")
    login(token=token)
    api = HfApi(token=token)
    username = api.whoami()["name"]
    src_repo = upload_source(api, username)
    status_path = ROOT / "data" / "gpu_job_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = submit(api, src_repo)
    except Exception as exc:
        payload = {
            "status": "blocked",
            "error": str(exc),
            "src_repo": src_repo,
            "flavor": FLAVOR,
            "model": os.environ.get("LIFEMEM_MODEL", "Qwen/Qwen3.5-4B"),
            "hint": (
                "Hugging Face Jobs needs a positive credit balance on the submitting "
                "namespace. Add credits at https://huggingface.co/settings/billing "
                "then re-run: uv run python "
                "autoresearch/mitigating_identity_essentialism_lifemem_2026_09_09/scripts/submit_hf_job.py"
            ),
        }
        status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 2
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
