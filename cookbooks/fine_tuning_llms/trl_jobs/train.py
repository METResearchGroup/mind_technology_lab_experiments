"""SFT script for Hugging Face Jobs.

Install dependencies from the repository root:

    uv sync --extra fine_tuning_llms

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py
"""

from pathlib import Path

from datasets import load_dataset
from trl import SFTConfig, SFTTrainer

from lib.timestamp_utils import get_current_timestamp
from shared.aws.constants import DEFAULT_BUCKET, DEFAULT_REGION_NAME
from shared.aws.upload_directory_to_s3 import upload_directory
from shared.telemetry.wandb import start_run

MODEL_NAME = "Qwen/Qwen2.5-0.5B"
DATASET_NAME = "trl-lib/Capybara"

WANDB_PROJECT = "fine_tuning_llms"
WANDB_GROUP = "trl_jobs"
RUN_NAME = f"Qwen2.5-0.5B_{get_current_timestamp()}"

# Same folder path as this cookbook, then one directory per run.
ARTIFACT_PREFIX = "cookbooks/fine_tuning_llms/trl_jobs"
OUTPUT_DIR = Path("/tmp") / RUN_NAME


def artifact_s3_uri() -> str:
    """Return the S3 prefix for this run's saved model."""
    return f"s3://{DEFAULT_BUCKET}/{ARTIFACT_PREFIX}/{RUN_NAME}"


def main() -> None:
    dataset = load_dataset(DATASET_NAME, split="train")
    with start_run(
        WANDB_PROJECT,
        WANDB_GROUP,
        RUN_NAME,
        config={"model": MODEL_NAME, "dataset": DATASET_NAME},
    ):
        training_args = SFTConfig(
            output_dir=str(OUTPUT_DIR),
            save_strategy="no",
            report_to="wandb",
            run_name=RUN_NAME,
            logging_strategy="steps",
            logging_steps=10,
        )
        trainer = SFTTrainer(
            model=MODEL_NAME,
            args=training_args,
            train_dataset=dataset,
        )
        trainer.train()
        trainer.save_model(str(OUTPUT_DIR))
        upload_directory(
            OUTPUT_DIR,
            artifact_s3_uri(),
            region=DEFAULT_REGION_NAME,
        )


if __name__ == "__main__":
    main()
