#!/usr/bin/env python3
"""Run the LifeMem Qwen job on a GPU pod when Hugging Face Jobs is billing-blocked.

The workload is still `scripts/hf_job.py` (Qwen/Qwen3.5-4B + per-agent LoRA).
Hugging Face Jobs remains the default path in `submit_hf_job.py`.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from huggingface_hub import HfApi, login
from lifemem.artifacts import DEFAULT_RESULTS_REPO, DEFAULT_SRC_REPO, aws_credentials

RUNPOD_API = "https://rest.runpod.io/v1/pods"
IMAGE = os.environ.get(
    "LIFEMEM_RUNPOD_IMAGE", "pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel"
)
GPU_TYPES = [
    "NVIDIA RTX A5000",
    "NVIDIA L4",
    "NVIDIA GeForce RTX 4090",
    "NVIDIA A40",
]
BOOTSTRAP = r"""
set -euxo pipefail
python -m pip install -q --upgrade pip
python -m pip install -q 'transformers>=5.0.0' peft accelerate pillow huggingface_hub boto3 torchvision numpy safetensors
python - <<'PY'
import os, runpy, sys
from huggingface_hub import snapshot_download
src = snapshot_download(
    repo_id=os.environ.get("LIFEMEM_SRC_REPO", "mtorres98/lifemem-replication-src"),
    repo_type="dataset",
    token=os.environ.get("HF_TOKEN"),
)
os.environ["LIFEMEM_SRC_MOUNT"] = src
sys.path.insert(0, src)
runpy.run_path(f"{src}/scripts/hf_job.py", run_name="__main__")
PY
"""


def _request(method: str, url: str, body: dict | None = None) -> dict:
    key = os.environ.get("RUNPOD_API_KEY")
    if not key:
        raise SystemExit("RUNPOD_API_KEY is required")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"RunPod {exc.code}: {detail}") from exc


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
            "pyproject.toml",
            "README.md",
        ],
        commit_message="LifeMem Qwen GPU job sources",
    )
    return repo_id


def create_pod(src_repo: str) -> dict:
    key, secret = aws_credentials()
    env = {
        "HF_TOKEN": os.environ["HF_TOKEN"],
        "LIFEMEM_SRC_REPO": src_repo,
        "LIFEMEM_RESULTS_REPO": os.environ.get(
            "LIFEMEM_RESULTS_REPO", DEFAULT_RESULTS_REPO
        ),
        "LIFEMEM_N_AGENTS": os.environ.get("LIFEMEM_N_AGENTS", "8"),
        "LIFEMEM_N_WAVES": os.environ.get("LIFEMEM_N_WAVES", "6"),
        "LIFEMEM_EVENTS_PER_WAVE": os.environ.get("LIFEMEM_EVENTS_PER_WAVE", "8"),
        "LIFEMEM_MODEL": os.environ.get("LIFEMEM_MODEL", "Qwen/Qwen3.5-4B"),
        "LIFEMEM_HARDWARE": "runpod-gpu",
        "LIFEMEM_PROGRESS": "1",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "TOKENIZERS_PARALLELISM": "false",
    }
    if key and secret:
        env["AWS_ACCESS_KEY_ID"] = key
        env["AWS_SECRET_ACCESS_KEY"] = secret
    body = {
        "name": "lifemem-qwen-4b",
        "imageName": IMAGE,
        "cloudType": os.environ.get("LIFEMEM_RUNPOD_CLOUD", "SECURE"),
        "computeType": "GPU",
        "gpuTypeIds": GPU_TYPES,
        "gpuTypePriority": "availability",
        "gpuCount": 1,
        "containerDiskInGb": 80,
        "volumeInGb": 20,
        "minRAMPerGPU": 16,
        "interruptible": False,
        "env": env,
        "dockerStartCmd": ["bash", "-lc", BOOTSTRAP.strip()],
    }
    return _request("POST", RUNPOD_API, body)


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required")
    login(token=token)
    api = HfApi(token=token)
    username = api.whoami()["name"]
    src_repo = os.environ.get("LIFEMEM_SRC_REPO", DEFAULT_SRC_REPO)
    if "--skip-upload" not in sys.argv:
        src_repo = upload_source(api, username)
    pod = create_pod(src_repo)
    payload = {
        "status": "submitted",
        "provider": "runpod",
        "id": pod.get("id"),
        "url": f"https://www.runpod.io/console/pods/{pod.get('id')}",
        "flavor": pod.get("gpu")
        or (pod.get("machine") or {}).get("gpuDisplayName")
        or "runpod-gpu",
        "timeout": "until-exit",
        "src_repo": src_repo,
        "n_agents": int(os.environ.get("LIFEMEM_N_AGENTS", "8")),
        "n_waves": int(os.environ.get("LIFEMEM_N_WAVES", "6")),
        "model": os.environ.get("LIFEMEM_MODEL", "Qwen/Qwen3.5-4B"),
        "hint": (
            "Hugging Face Jobs returned 402 on this token, so the same "
            "scripts/hf_job.py Qwen LoRA suite is running on a GPU pod. "
            "Results still upload to the Hub dataset and S3."
        ),
        "pod": {
            "desiredStatus": pod.get("desiredStatus"),
            "image": pod.get("image"),
            "machine": pod.get("machine"),
        },
    }
    status_path = ROOT / "data" / "gpu_job_status.json"
    status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
