"""Basic SFT loop for SmolLM2 with TRL.

Install from the repository root:

    uv sync --extra fine_tuning_llms

Run from the repository root:

    uv run python cookbooks/fine_tuning_llms/huggingface_fine_tuning_trl/train.py
"""

from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

MODEL_NAME = "HuggingFaceTB/SmolLM2-135M"
CHAT_TEMPLATE_PATH = "HuggingFaceTB/SmolLM2-135M-Instruct"
DATASET_NAME = "HuggingFaceTB/smoltalk"
OUTPUT_DIR = Path(__file__).resolve().parent / "sft_output"


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dataset = load_dataset(DATASET_NAME, "all")
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(device)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    training_args = SFTConfig(
        output_dir=str(OUTPUT_DIR),
        max_steps=1000,
        per_device_train_batch_size=4,
        learning_rate=5e-5,
        logging_steps=10,
        save_steps=100,
        eval_strategy="steps",
        eval_steps=50,
        chat_template_path=CHAT_TEMPLATE_PATH,
        eos_token="<|im_end|>",
    )
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        processing_class=tokenizer,
    )
    trainer.train()


if __name__ == "__main__":
    main()
