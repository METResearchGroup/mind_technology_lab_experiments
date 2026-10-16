"""Submit the LoRA train script as a Hugging Face Job.

Reuses the job helpers from ``cookbooks/fine_tuning_llms/trl_jobs/runner.py``.
The train script imports that cookbook's model and dataset constants, so the
job also mounts ``trl_jobs``.

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_lora_training/runner.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_FINE_TUNING_DIR = Path(__file__).resolve().parent.parent
if str(_FINE_TUNING_DIR) not in sys.path:
    sys.path.insert(0, str(_FINE_TUNING_DIR))

from huggingface_hub import run_uv_job  # noqa: E402
from trl_jobs.runner import (  # noqa: E402
    JOB_TIMEOUT,
    REPO_MOUNT_PATH,
    TRAIN_JOB_FLAVOR,
    TRL_JOBS_MOUNT_PATH,
    _aws_and_hf_secrets,
    _shared_volumes,
    _sync_python_modules_volume,
)

from lib.load_env_vars import EnvVarsContainer  # noqa: E402
from shared.aws.constants import DEFAULT_REGION_NAME  # noqa: E402

LORA_DIR = Path(__file__).resolve().parent
TRAIN_SCRIPT = LORA_DIR / "train.py"
FINE_TUNING_MOUNT_PATH = str(Path(TRL_JOBS_MOUNT_PATH).parent)


def launch_train_job() -> object:
    """Submit ``train.py`` for LoRA SFT on Hugging Face Jobs."""
    secrets = _aws_and_hf_secrets()
    secrets["WANDB_API_KEY"] = EnvVarsContainer.get_env_var(
        "WANDB_API_KEY", required=True
    )
    pythonpath = f"{REPO_MOUNT_PATH}:{FINE_TUNING_MOUNT_PATH}"

    return run_uv_job(
        str(TRAIN_SCRIPT),
        dependencies=["trl", "peft", "wandb", "boto3"],
        flavor=TRAIN_JOB_FLAVOR,
        timeout=JOB_TIMEOUT,
        volumes=[*_shared_volumes(), _sync_python_modules_volume()],
        env={
            "PYTHONPATH": pythonpath,
            "AWS_DEFAULT_REGION": DEFAULT_REGION_NAME,
            "AWS_REGION": DEFAULT_REGION_NAME,
        },
        secrets=secrets,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Submit the LoRA SFT script to Hugging Face Jobs."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="train",
        choices=("train",),
        help="Which job to launch (default: train).",
    )
    return parser


def main() -> None:
    build_parser().parse_args()
    job = launch_train_job()
    print(job)


if __name__ == "__main__":
    main()
