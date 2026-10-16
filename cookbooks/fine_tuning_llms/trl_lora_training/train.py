"""LoRA SFT script for Hugging Face Jobs.

Same model, dataset, and artifact layout as ``trl_jobs/train.py``. Adapter
settings follow https://huggingface.co/docs/trl/en/lora_without_regret.

Install dependencies from the repository root:

    uv sync --extra fine_tuning_llms

Launch from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_lora_training/runner.py
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FINE_TUNING_DIR = Path(__file__).resolve().parent.parent
if (_REPO_ROOT / "lib").is_dir() and (_REPO_ROOT / "shared").is_dir():
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
if (_FINE_TUNING_DIR / "trl_jobs").is_dir() and str(_FINE_TUNING_DIR) not in sys.path:
    sys.path.insert(0, str(_FINE_TUNING_DIR))

from datasets import load_dataset  # noqa: E402
from peft import LoraConfig  # noqa: E402
from trl import SFTConfig, SFTTrainer  # noqa: E402
from trl_jobs.train import DATASET_NAME, MODEL_NAME, WANDB_PROJECT  # noqa: E402

from lib.timestamp_utils import get_current_timestamp  # noqa: E402
from shared.aws.constants import DEFAULT_BUCKET, DEFAULT_REGION_NAME  # noqa: E402
from shared.aws.upload_directory_to_s3 import upload_directory  # noqa: E402
from shared.telemetry.wandb import start_run  # noqa: E402

# SFT LoRA from the TRL guide: every linear layer, rank 256, and a learning
# rate above the full fine-tuning default.
LORA_RANK = 256
LORA_ALPHA = 16
LORA_TARGET_MODULES = "all-linear"
LEARNING_RATE = 2e-4

WANDB_GROUP = "trl_lora_training"
RUN_NAME = f"{MODEL_NAME.rsplit('/', 1)[-1]}_lora_{get_current_timestamp()}"

ARTIFACT_PREFIX = "cookbooks/fine_tuning_llms/trl_lora_training"
OUTPUT_DIR = Path("/tmp") / RUN_NAME


def artifact_s3_uri() -> str:
    """Return the S3 prefix for this run's saved adapter."""
    return f"s3://{DEFAULT_BUCKET}/{ARTIFACT_PREFIX}/{RUN_NAME}"


def main() -> None:
    dataset = load_dataset(DATASET_NAME, split="train")
    peft_config = LoraConfig(
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        target_modules=LORA_TARGET_MODULES,
    )
    with start_run(
        WANDB_PROJECT,
        WANDB_GROUP,
        RUN_NAME,
        config={
            "model": MODEL_NAME,
            "dataset": DATASET_NAME,
            "learning_rate": LEARNING_RATE,
            "lora_r": LORA_RANK,
            "lora_alpha": LORA_ALPHA,
            "lora_target_modules": LORA_TARGET_MODULES,
        },
    ):
        training_args = SFTConfig(
            output_dir=str(OUTPUT_DIR),
            learning_rate=LEARNING_RATE,
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
            peft_config=peft_config,
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
