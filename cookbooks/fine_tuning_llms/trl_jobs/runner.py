"""Submit `train.py` as a Hugging Face Job.

Uses the Python API from https://huggingface.co/docs/trl/jobs_training.

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import run_uv_job, sync_job_volume

# annoying workaround for now.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.load_env_vars import EnvVarsContainer  # noqa: E402
from shared.aws.constants import DEFAULT_REGION_NAME  # noqa: E402

TRAIN_SCRIPT = Path(__file__).resolve().with_name("train.py")
SHARED_PACKAGE_DIR = REPO_ROOT / "shared"
LIB_PACKAGE_DIR = REPO_ROOT / "lib"
REPO_MOUNT_PATH = "/mnt/repo"
SHARED_MOUNT_PATH = "/mnt/repo/shared"
LIB_MOUNT_PATH = "/mnt/repo/lib"
JOB_FLAVOR = "a100-large"
JOB_TIMEOUT = "2h"


def launch_job() -> object:
    hf_token = EnvVarsContainer.get_env_var("HF_TOKEN", required=True)
    wandb_api_key = EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)
    aws_access_key_id = EnvVarsContainer.get_env_var("AWS_ACCESS_KEY_ID", required=True)
    aws_secret_access_key = EnvVarsContainer.get_env_var(
        "AWS_ACCESS_KEY_SECRET", required=True
    )

    volumes = [
        sync_job_volume(SHARED_PACKAGE_DIR, SHARED_MOUNT_PATH),
        sync_job_volume(LIB_PACKAGE_DIR, LIB_MOUNT_PATH),
    ]

    return run_uv_job(
        str(TRAIN_SCRIPT),
        dependencies=["trl", "wandb", "boto3"],
        flavor=JOB_FLAVOR,
        timeout=JOB_TIMEOUT,
        volumes=volumes,
        env={
            "PYTHONPATH": REPO_MOUNT_PATH,
            "AWS_DEFAULT_REGION": DEFAULT_REGION_NAME,
            "AWS_REGION": DEFAULT_REGION_NAME,
        },
        secrets={
            "HF_TOKEN": hf_token,
            "WANDB_API_KEY": wandb_api_key,
            "AWS_ACCESS_KEY_ID": aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
        },
    )


def main() -> None:
    job = launch_job()
    print(job)


if __name__ == "__main__":
    main()
