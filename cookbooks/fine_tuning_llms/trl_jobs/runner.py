"""Submit `train.py` as a Hugging Face Job.

Uses the Python API from https://huggingface.co/docs/trl/jobs_training.
Does not train locally. Requires allowlisted secrets via ``EnvVarsContainer``.

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py
"""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import run_uv_job, sync_job_volume

from lib.load_env_vars import EnvVarsContainer

TRAIN_SCRIPT = Path(__file__).resolve().with_name("train.py")
REPO_ROOT = Path(__file__).resolve().parents[3]
SHARED_PACKAGE_DIR = REPO_ROOT / "shared"
REPO_MOUNT_PATH = "/mnt/repo"
SHARED_MOUNT_PATH = "/mnt/repo/shared"
JOB_FLAVOR = "a100-large"
JOB_TIMEOUT = "2h"


def launch_job() -> object:
    hf_token = EnvVarsContainer.get_env_var("HF_TOKEN", required=True)
    wandb_api_key = EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)

    volume = sync_job_volume(SHARED_PACKAGE_DIR, SHARED_MOUNT_PATH)

    return run_uv_job(
        str(TRAIN_SCRIPT),
        dependencies=["trl", "wandb"],
        flavor=JOB_FLAVOR,
        timeout=JOB_TIMEOUT,
        volumes=[volume],
        env={"PYTHONPATH": REPO_MOUNT_PATH},
        secrets={"HF_TOKEN": hf_token, "WANDB_API_KEY": wandb_api_key},
    )


def main() -> None:
    job = launch_job()
    print(job)


if __name__ == "__main__":
    main()
