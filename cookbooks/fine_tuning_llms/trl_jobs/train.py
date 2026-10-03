"""SFT script for Hugging Face Jobs.

Install dependencies from the repository root:

    uv sync --extra fine_tuning_llms

Push the result to the Hub before the job ends; the machine is deleted afterward.
Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py
"""

from datasets import load_dataset
from trl import SFTTrainer

MODEL_NAME = "Qwen/Qwen2.5-0.5B"
DATASET_NAME = "trl-lib/Capybara"
HUB_MODEL_ID = "Qwen2.5-0.5B-SFT"


def main() -> None:
    dataset = load_dataset(DATASET_NAME, split="train")
    trainer = SFTTrainer(
        model=MODEL_NAME,
        train_dataset=dataset,
    )
    trainer.train()
    trainer.push_to_hub(HUB_MODEL_ID)


if __name__ == "__main__":
    main()
