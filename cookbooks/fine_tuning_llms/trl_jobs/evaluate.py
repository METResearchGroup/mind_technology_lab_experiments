"""Compare base vs SFT replies on the first Capybara conversations.

Runs on a Hugging Face Job. Submit from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py evaluate

Writes a JSON artifact to S3 with prompt / base / fine-tuned outputs.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

from datasets import load_dataset

# HF Jobs uploads this file alone; sibling modules arrive via the volume mount.
_TRL_JOBS_MOUNT = Path("/mnt/repo/cookbooks/fine_tuning_llms/trl_jobs")
if _TRL_JOBS_MOUNT.is_dir() and str(_TRL_JOBS_MOUNT) not in sys.path:
    sys.path.insert(0, str(_TRL_JOBS_MOUNT))
_LOCAL_DIR = Path(__file__).resolve().parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

_inference = importlib.import_module("inference")
DATASET_NAME = _inference.DATASET_NAME
DEFAULT_EVAL_LIMIT = _inference.DEFAULT_EVAL_LIMIT
DEFAULT_MAX_NEW_TOKENS = _inference.DEFAULT_MAX_NEW_TOKENS
DEFAULT_SFT_S3_URI = _inference.DEFAULT_SFT_S3_URI
EVAL_RESULTS_S3_URI = _inference.EVAL_RESULTS_S3_URI
MODEL_NAME = _inference.MODEL_NAME
download_s3_prefix = _inference.download_s3_prefix
generate_reply = _inference.generate_reply
load_causal_lm = _inference.load_causal_lm
load_tokenizer = _inference.load_tokenizer
prompt_messages = _inference.prompt_messages
render_prompt = _inference.render_prompt
upload_json_to_s3 = _inference.upload_json_to_s3


def run_comparison(
    *,
    s3_uri: str = DEFAULT_SFT_S3_URI,
    results_s3_uri: str = EVAL_RESULTS_S3_URI,
    limit: int = DEFAULT_EVAL_LIMIT,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
) -> str:
    """Compare models, upload JSON results to S3, and return the results URI."""
    dataset = load_dataset(DATASET_NAME, split="train")
    examples = dataset.select(range(min(limit, len(dataset))))

    print(f"Downloading SFT checkpoint from {s3_uri}")
    checkpoint_dir = download_s3_prefix(s3_uri)

    # Tokenizer from the SFT run so both models share the trained chat template.
    tokenizer = load_tokenizer(checkpoint_dir)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading base model {MODEL_NAME}")
    base_model = load_causal_lm(MODEL_NAME)
    print(f"Loading fine-tuned model from {checkpoint_dir}")
    sft_model = load_causal_lm(checkpoint_dir)

    conversations: list[dict[str, Any]] = []
    for index, row in enumerate(examples):
        example = dict(row)
        messages: list[dict[str, Any]] = list(example["messages"])
        prompt = prompt_messages(messages)
        prompt_text = render_prompt(tokenizer, prompt)

        print(f"\nGenerating conversation {index + 1}/{len(examples)}")
        base_output = generate_reply(
            base_model,
            tokenizer,
            prompt,
            max_new_tokens=max_new_tokens,
            prompt_text=prompt_text,
        )
        fine_tuned_output = generate_reply(
            sft_model,
            tokenizer,
            prompt,
            max_new_tokens=max_new_tokens,
            prompt_text=prompt_text,
        )
        conversations.append(
            {
                "index": index,
                "prompt": prompt_text,
                "base_output": base_output,
                "fine_tuned_output": fine_tuned_output,
            }
        )
        print(f"BASE: {base_output[:200]!r}")
        print(f"FINE-TUNED: {fine_tuned_output[:200]!r}")

    payload = {
        "base_model": MODEL_NAME,
        "dataset": DATASET_NAME,
        "sft_s3_uri": s3_uri,
        "limit": len(conversations),
        "max_new_tokens": max_new_tokens,
        "conversations": conversations,
    }
    upload_json_to_s3(payload, results_s3_uri)
    print("Done.")
    return results_s3_uri


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare base and SFT model replies on Capybara."
    )
    parser.add_argument(
        "--s3-uri",
        default=DEFAULT_SFT_S3_URI,
        help="S3 URI of the fine-tuned checkpoint directory.",
    )
    parser.add_argument(
        "--results-s3-uri",
        default=EVAL_RESULTS_S3_URI,
        help="S3 URI where the comparison JSON will be written.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_EVAL_LIMIT,
        help="Number of training conversations to evaluate.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=DEFAULT_MAX_NEW_TOKENS,
        help="Maximum new tokens to generate per reply.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_comparison(
        s3_uri=args.s3_uri,
        results_s3_uri=args.results_s3_uri,
        limit=args.limit,
        max_new_tokens=args.max_new_tokens,
    )


if __name__ == "__main__":
    main()
