"""Submit train or evaluate scripts as Hugging Face Jobs.

Uses the Python API from https://huggingface.co/docs/trl/jobs_training.

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py
    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py evaluate
    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py evaluate-mmlu
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from huggingface_hub import HfApi, run_uv_job, sync_job_volume

# annoying workaround for now.
REPO_ROOT = Path(__file__).resolve().parents[3]
TRL_JOBS_DIR = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(TRL_JOBS_DIR) not in sys.path:
    sys.path.insert(0, str(TRL_JOBS_DIR))

from inference import (  # noqa: E402
    EVAL_RESULTS_FILENAME,
    EVAL_RESULTS_S3_URI,
    MMLU_RESULTS_FILENAME,
    MMLU_RESULTS_S3_URI,
    download_s3_object,
)

from lib.load_env_vars import EnvVarsContainer  # noqa: E402
from shared.aws.constants import DEFAULT_REGION_NAME  # noqa: E402

TRAIN_SCRIPT = TRL_JOBS_DIR / "train.py"
EVAL_SCRIPT = TRL_JOBS_DIR / "evaluate.py"
EVAL_MMLU_SCRIPT = TRL_JOBS_DIR / "evaluate_mmlu.py"
SHARED_PACKAGE_DIR = REPO_ROOT / "shared"
LIB_PACKAGE_DIR = REPO_ROOT / "lib"
REPO_MOUNT_PATH = "/mnt/repo"
SHARED_MOUNT_PATH = "/mnt/repo/shared"
LIB_MOUNT_PATH = "/mnt/repo/lib"
TRL_JOBS_MOUNT_PATH = "/mnt/repo/cookbooks/fine_tuning_llms/trl_jobs"
LOCAL_EVAL_RESULTS_PATH = TRL_JOBS_DIR / "outputs" / EVAL_RESULTS_FILENAME
LOCAL_MMLU_RESULTS_PATH = TRL_JOBS_DIR / "outputs" / MMLU_RESULTS_FILENAME
TRAIN_JOB_FLAVOR = "a100-large"
EVAL_JOB_FLAVOR = "t4-small"
JOB_TIMEOUT = "2h"
MMLU_JOB_TIMEOUT = "4h"
JOB_POLL_SECONDS = 30


def _aws_and_hf_secrets() -> dict[str, str]:
    return {
        "HF_TOKEN": EnvVarsContainer.get_env_var("HF_TOKEN", required=True),
        "AWS_ACCESS_KEY_ID": EnvVarsContainer.get_env_var(
            "AWS_ACCESS_KEY_ID", required=True
        ),
        "AWS_SECRET_ACCESS_KEY": EnvVarsContainer.get_env_var(
            "AWS_ACCESS_KEY_SECRET", required=True
        ),
    }


def _export_aws_credentials(secrets: dict[str, str]) -> None:
    """Export AWS keys so local boto3 can download evaluation artifacts."""
    os.environ["AWS_ACCESS_KEY_ID"] = secrets["AWS_ACCESS_KEY_ID"]
    os.environ["AWS_SECRET_ACCESS_KEY"] = secrets["AWS_SECRET_ACCESS_KEY"]
    os.environ.setdefault("AWS_DEFAULT_REGION", DEFAULT_REGION_NAME)
    os.environ.setdefault("AWS_REGION", DEFAULT_REGION_NAME)


def _shared_volumes() -> list[object]:
    return [
        sync_job_volume(SHARED_PACKAGE_DIR, SHARED_MOUNT_PATH),
        sync_job_volume(LIB_PACKAGE_DIR, LIB_MOUNT_PATH),
    ]


def launch_train_job() -> object:
    """Submit ``train.py`` for SFT on Hugging Face Jobs."""
    secrets = _aws_and_hf_secrets()
    secrets["WANDB_API_KEY"] = EnvVarsContainer.get_env_var(
        "WANDB_API_KEY", required=True
    )

    return run_uv_job(
        str(TRAIN_SCRIPT),
        dependencies=["trl", "wandb", "boto3"],
        flavor=TRAIN_JOB_FLAVOR,
        timeout=JOB_TIMEOUT,
        volumes=_shared_volumes(),
        env={
            "PYTHONPATH": REPO_MOUNT_PATH,
            "AWS_DEFAULT_REGION": DEFAULT_REGION_NAME,
            "AWS_REGION": DEFAULT_REGION_NAME,
        },
        secrets=secrets,
    )


def _sync_python_modules_volume() -> object:
    """Sync only ``*.py`` from this folder (skip static assets / PDF)."""
    staging = Path(tempfile.mkdtemp(prefix="trl_jobs_eval_"))
    for path in TRL_JOBS_DIR.glob("*.py"):
        shutil.copy2(path, staging / path.name)
    return sync_job_volume(staging, TRL_JOBS_MOUNT_PATH)


def launch_evaluate_job() -> object:
    """Submit ``evaluate.py`` to compare base vs SFT replies.

    Mounts this cookbook's Python modules so the job can ``import inference``.
    The SFT weights are downloaded from S3 onto the job machine only.
    """
    volumes = [
        *_shared_volumes(),
        _sync_python_modules_volume(),
    ]
    pythonpath = f"{REPO_MOUNT_PATH}:{TRL_JOBS_MOUNT_PATH}"

    return run_uv_job(
        str(EVAL_SCRIPT),
        dependencies=["transformers", "datasets", "torch", "accelerate", "boto3"],
        flavor=EVAL_JOB_FLAVOR,
        timeout=JOB_TIMEOUT,
        volumes=volumes,
        env={
            "PYTHONPATH": pythonpath,
            "AWS_DEFAULT_REGION": DEFAULT_REGION_NAME,
            "AWS_REGION": DEFAULT_REGION_NAME,
        },
        secrets=_aws_and_hf_secrets(),
    )


def launch_evaluate_mmlu_job() -> object:
    """Submit ``evaluate_mmlu.py`` to score base vs SFT on five MMLU subjects.

    Mounts this cookbook's Python modules so the job can ``import inference``.
    The SFT weights are downloaded from S3 onto the job machine only.
    """
    volumes = [
        *_shared_volumes(),
        _sync_python_modules_volume(),
    ]
    pythonpath = f"{REPO_MOUNT_PATH}:{TRL_JOBS_MOUNT_PATH}"

    return run_uv_job(
        str(EVAL_MMLU_SCRIPT),
        dependencies=[
            "transformers",
            "datasets",
            "torch",
            "accelerate",
            "boto3",
            # 4.2.8 loads MMLU from cais/mmlu. Older releases still call
            # lukaemon/mmlu, whose dataset script datasets 4.x rejects.
            "deepeval==4.2.8",
            "pandas",
        ],
        flavor=EVAL_JOB_FLAVOR,
        timeout=MMLU_JOB_TIMEOUT,
        volumes=volumes,
        env={
            "PYTHONPATH": pythonpath,
            "AWS_DEFAULT_REGION": DEFAULT_REGION_NAME,
            "AWS_REGION": DEFAULT_REGION_NAME,
            "DEEPEVAL_TELEMETRY_OPT_OUT": "YES",
        },
        secrets=_aws_and_hf_secrets(),
    )


def wait_for_job(job_id: str) -> object:
    """Block until the HF Job reaches a terminal stage."""
    api = HfApi()
    terminal = {"COMPLETED", "ERROR", "CANCELED", "CANCELLED"}
    while True:
        info = api.inspect_job(job_id=job_id)
        stage = str(info.status.stage)
        print(f"Job {job_id}: {stage}")
        if stage in terminal:
            if stage != "COMPLETED":
                raise RuntimeError(
                    f"Evaluate job finished with stage={stage}: {info.status.message}"
                )
            return info
        time.sleep(JOB_POLL_SECONDS)


def download_eval_results(
    *,
    results_s3_uri: str = EVAL_RESULTS_S3_URI,
    local_path: Path = LOCAL_EVAL_RESULTS_PATH,
) -> Path:
    """Download the evaluation JSON from S3 to this cookbook's outputs folder."""
    secrets = _aws_and_hf_secrets()
    _export_aws_credentials(secrets)
    return download_s3_object(results_s3_uri, local_path)


def run_evaluate_and_download() -> Path:
    """Launch evaluate, wait for completion, then download the JSON locally."""
    job = launch_evaluate_job()
    print(job)
    job_id = getattr(job, "id", None)
    if not job_id:
        raise RuntimeError(f"Could not determine job id from {job!r}")
    wait_for_job(str(job_id))
    local_path = download_eval_results()
    print(f"Local results: {local_path}")
    return local_path


def download_mmlu_results(
    *,
    results_s3_uri: str = MMLU_RESULTS_S3_URI,
    local_path: Path = LOCAL_MMLU_RESULTS_PATH,
) -> Path:
    """Download the MMLU score JSON from S3 to this cookbook's outputs folder."""
    secrets = _aws_and_hf_secrets()
    _export_aws_credentials(secrets)
    return download_s3_object(results_s3_uri, local_path)


def run_evaluate_mmlu_and_download() -> Path:
    """Launch the MMLU eval, wait for completion, then download the JSON."""
    job = launch_evaluate_mmlu_job()
    print(job)
    job_id = getattr(job, "id", None)
    if not job_id:
        raise RuntimeError(f"Could not determine job id from {job!r}")
    wait_for_job(str(job_id))
    local_path = download_mmlu_results()
    print(f"Local results: {local_path}")
    return local_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Submit trl_jobs train or evaluate scripts to HF Jobs."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="train",
        choices=("train", "evaluate", "evaluate-mmlu"),
        help="Which job to launch (default: train).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "evaluate":
        run_evaluate_and_download()
    elif args.command == "evaluate-mmlu":
        run_evaluate_mmlu_and_download()
    else:
        job = launch_train_job()
        print(job)


if __name__ == "__main__":
    main()
