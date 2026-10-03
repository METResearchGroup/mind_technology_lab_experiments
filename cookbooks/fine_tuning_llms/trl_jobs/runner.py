"""Submit `train.py` as a Hugging Face Job.

Uses the Python API from https://huggingface.co/docs/trl/jobs_training.
Does not train locally. Requires `HF_TOKEN` in the environment.

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py
"""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import run_uv_job

TRAIN_SCRIPT = Path(__file__).resolve().with_name("train.py")
JOB_FLAVOR = "a100-large"
JOB_TIMEOUT = "2h"


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is not set")

    job = run_uv_job(
        str(TRAIN_SCRIPT),
        dependencies=["trl"],
        flavor=JOB_FLAVOR,
        secrets={"HF_TOKEN": token},
        timeout=JOB_TIMEOUT,
    )
    print(job)


if __name__ == "__main__":
    main()
