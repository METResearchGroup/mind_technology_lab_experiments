#!/usr/bin/env python3
"""Run scripts/hf_job.py on a GPU pod when Hugging Face Jobs returns 402.

Uses the same CUDA image as submit_hf_job.py (pytorch/pytorch:2.6.0-cuda12.4).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from huggingface_hub import HfApi, login
from lifemem.artifacts import DEFAULT_RESULTS_REPO, DEFAULT_SRC_REPO, aws_credentials

RUNPOD_REST = "https://rest.runpod.io/v1/pods"
RUNPOD_GQL = "https://api.runpod.io/graphql"
IMAGE = os.environ.get(
    "LIFEMEM_RUNPOD_IMAGE",
    "pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel",
)
GPU_TYPES = [
    "NVIDIA L4",
    "NVIDIA RTX A5000",
    "NVIDIA GeForce RTX 4090",
    "NVIDIA A40",
    "NVIDIA RTX A6000",
    "NVIDIA GeForce RTX 3090",
]
# Official pytorch image has Python/urllib; do not pip-install before the script.
INNER_CMD = """
set -euxo pipefail
export PYTHONUNBUFFERED=1
export HF_HUB_ENABLE_HF_TRANSFER=0
mkdir -p /root/.ssh
if [ -n "${PUBLIC_KEY:-}" ]; then
  echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
fi
if command -v service >/dev/null 2>&1; then
  service ssh start || true
fi
/usr/sbin/sshd || true
python3 - <<'PY'
import os
import urllib.request
repo = os.environ.get("LIFEMEM_SRC_REPO", "mtorres98/lifemem-replication-src")
url = (
    "https://huggingface.co/datasets/"
    + repo
    + "/resolve/main/scripts/gpu_bootstrap.sh"
)
urllib.request.urlretrieve(url, "/tmp/gpu_bootstrap.sh")
print("downloaded", url, flush=True)
PY
bash /tmp/gpu_bootstrap.sh
status=$?
if [ "$status" -ne 0 ]; then
  echo "lifemem job failed with $status; sleeping for SSH inspect"
  sleep 1800
fi
exit "$status"
"""


def _env_pairs() -> list[dict[str, str]]:
    key, secret = aws_credentials()
    env = {
        "HF_TOKEN": os.environ["HF_TOKEN"],
        "LIFEMEM_SRC_REPO": os.environ.get("LIFEMEM_SRC_REPO", DEFAULT_SRC_REPO),
        "LIFEMEM_RESULTS_REPO": os.environ.get(
            "LIFEMEM_RESULTS_REPO", DEFAULT_RESULTS_REPO
        ),
        "LIFEMEM_N_AGENTS": os.environ.get("LIFEMEM_N_AGENTS", "8"),
        "LIFEMEM_N_WAVES": os.environ.get("LIFEMEM_N_WAVES", "6"),
        "LIFEMEM_EVENTS_PER_WAVE": os.environ.get("LIFEMEM_EVENTS_PER_WAVE", "8"),
        "LIFEMEM_MODEL": os.environ.get("LIFEMEM_MODEL", "Qwen/Qwen3.5-4B"),
        "LIFEMEM_HARDWARE": "runpod-gpu",
        "LIFEMEM_PROGRESS": "1",
        "LIFEMEM_TRAIN_BATCH_SIZE": os.environ.get("LIFEMEM_TRAIN_BATCH_SIZE", "1"),
        "LIFEMEM_MAX_TRAIN_SEQ_LEN": os.environ.get("LIFEMEM_MAX_TRAIN_SEQ_LEN", "768"),
        "LIFEMEM_GEN_BATCH_SIZE": os.environ.get("LIFEMEM_GEN_BATCH_SIZE", "4"),
        "TOKENIZERS_PARALLELISM": "false",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    }
    public_key = os.environ.get("LIFEMEM_SSH_PUBLIC_KEY")
    if public_key:
        env["PUBLIC_KEY"] = public_key
    if key and secret:
        env["AWS_ACCESS_KEY_ID"] = key
        env["AWS_SECRET_ACCESS_KEY"] = secret
    return [{"key": k, "value": v} for k, v in env.items()]


def _http(method: str, url: str, body: dict | None = None) -> tuple[int, dict | str]:
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
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(detail)
        except json.JSONDecodeError:
            return exc.code, detail


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


def _graphql_create(src_repo: str, gpu: str, cloud: str) -> tuple[int, dict | str]:
    env = _env_pairs()
    for item in env:
        if item["key"] == "LIFEMEM_SRC_REPO":
            item["value"] = src_repo
    query = """
    mutation($input: PodFindAndDeployOnDemandInput!) {
      podFindAndDeployOnDemand(input: $input) {
        id imageName desiredStatus gpuCount machineId
        machine { gpuDisplayName }
      }
    }
    """
    variables = {
        "input": {
            "cloudType": cloud,
            "gpuCount": 1,
            "volumeInGb": 20,
            "containerDiskInGb": 80,
            "minVcpuCount": 2,
            "minMemoryInGb": 15,
            "gpuTypeId": gpu,
            "name": "lifemem-qwen-4b",
            "imageName": IMAGE,
            "dockerArgs": "bash -c " + json.dumps(INNER_CMD.strip()),
            "volumeMountPath": "/workspace",
            "ports": "22/tcp",
            "startSsh": True,
            "startJupyter": False,
            "env": env,
        }
    }
    return _http("POST", RUNPOD_GQL, {"query": query, "variables": variables})


def _rest_create(src_repo: str, gpu: str, cloud: str) -> tuple[int, dict | str]:
    env = {item["key"]: item["value"] for item in _env_pairs()}
    env["LIFEMEM_SRC_REPO"] = src_repo
    body = {
        "name": "lifemem-qwen-4b",
        "imageName": IMAGE,
        "cloudType": cloud,
        "computeType": "GPU",
        "gpuTypeIds": [gpu],
        "gpuTypePriority": "availability",
        "gpuCount": 1,
        "containerDiskInGb": 80,
        "volumeInGb": 20,
        "minRAMPerGPU": 16,
        "interruptible": False,
        "ports": ["22/tcp"],
        "env": env,
        "dockerStartCmd": ["bash", "-c", INNER_CMD.strip()],
    }
    return _http("POST", RUNPOD_REST, body)


def create_pod(src_repo: str) -> dict:
    errors: list[str] = []
    clouds = ["SECURE", "COMMUNITY", "ALL"]
    # REST sets dockerStartCmd; GraphQL dockerArgs is not returned/applied.
    for gpu in GPU_TYPES:
        for cloud in clouds:
            for factory in (_rest_create,):
                status, payload = factory(src_repo, gpu, cloud)
                if status in {200, 201} and isinstance(payload, dict):
                    pod = (
                        payload.get("data", {}).get("podFindAndDeployOnDemand")
                        or payload
                    )
                    if isinstance(pod, dict) and pod.get("id"):
                        pod["requestedGpu"] = gpu
                        pod["requestedCloud"] = cloud
                        return pod
                    if payload.get("errors"):
                        errors.append(f"{gpu}/{cloud}: {payload['errors']}")
                        continue
                errors.append(f"{gpu}/{cloud} {factory.__name__} {status}: {payload}")
                if status == 1010 or (isinstance(payload, str) and "1010" in payload):
                    time.sleep(2)
                    continue
    raise SystemExit("Could not rent a GPU pod:\n" + "\n".join(errors[-20:]))


def terminate_pod(pod_id: str) -> tuple[int, dict | str]:
    gql = {
        "query": ("mutation($id: String!) { podTerminate(input: {podId: $id}) }"),
        "variables": {"id": pod_id},
    }
    status, payload = _http("POST", RUNPOD_GQL, gql)
    if status in {200, 201}:
        return status, payload
    return _http("DELETE", f"{RUNPOD_REST}/{pod_id}")


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
    os.environ["LIFEMEM_SRC_REPO"] = src_repo
    pod = create_pod(src_repo)
    payload = {
        "status": "submitted",
        "provider": "runpod",
        "id": pod.get("id"),
        "url": f"https://www.runpod.io/console/pods/{pod.get('id')}",
        "flavor": pod.get("requestedGpu")
        or (pod.get("machine") or {}).get("gpuDisplayName")
        or "runpod-gpu",
        "timeout": "until-exit",
        "src_repo": src_repo,
        "n_agents": int(os.environ.get("LIFEMEM_N_AGENTS", "8")),
        "n_waves": int(os.environ.get("LIFEMEM_N_WAVES", "6")),
        "model": os.environ.get("LIFEMEM_MODEL", "Qwen/Qwen3.5-4B"),
        "image": IMAGE,
        "hint": (
            "Hugging Face Jobs returned 402 on this token, so the same "
            "scripts/hf_job.py Qwen LoRA suite is running on a GPU pod "
            f"using {IMAGE}. Results still upload to the Hub dataset and S3."
        ),
        "pod": {
            "desiredStatus": pod.get("desiredStatus"),
            "image": pod.get("imageName") or pod.get("image"),
            "machine": pod.get("machine"),
            "cloud": pod.get("requestedCloud"),
        },
    }
    status_path = ROOT / "data" / "gpu_job_status.json"
    status_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
