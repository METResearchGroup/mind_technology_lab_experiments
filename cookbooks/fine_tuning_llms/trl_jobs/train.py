"""SFT script for Hugging Face Jobs.

Install dependencies from the repository root:

    uv sync --extra fine_tuning_llms

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py
"""

from datasets import load_dataset
from trl import SFTConfig, SFTTrainer

from lib.timestamp_utils import get_current_timestamp
from shared.telemetry.wandb import start_run

MODEL_NAME = "Qwen/Qwen2.5-0.5B"
DATASET_NAME = "trl-lib/Capybara"
HUB_MODEL_ID = "Qwen2.5-0.5B-SFT"

WANDB_PROJECT = "fine_tuning_llms"
WANDB_GROUP = "trl_jobs"
RUN_NAME = f"Qwen2.5-0.5B_{get_current_timestamp()}"


def main() -> None:
    dataset = load_dataset(DATASET_NAME, split="train")
    with start_run(
        WANDB_PROJECT,
        WANDB_GROUP,
        RUN_NAME,
        config={"model": MODEL_NAME, "dataset": DATASET_NAME},
    ):
        training_args = SFTConfig(
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


if __name__ == "__main__":
    main()
