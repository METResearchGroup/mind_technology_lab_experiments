"""Score base vs SFT models on five MMLU subjects with DeepEval.

Docs: https://deepeval.com/docs/benchmarks-mmlu

Runs on a Hugging Face Job. Submit from the repository root:

    uv run python cookbooks/fine_tuning_llms/trl_jobs/runner.py evaluate-mmlu

Writes a JSON artifact to S3 with one accuracy per subject for each model.
Accuracy is the share of test questions whose reply letter matches the key.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

import argparse
import gc
import importlib
import re
import sys
from pathlib import Path
from typing import Any

import deepeval
import torch
from deepeval.benchmarks import MMLU
from deepeval.benchmarks.mmlu.task import MMLUTask
from deepeval.models.base_model import DeepEvalBaseLLM

# HF Jobs uploads this file alone; sibling modules arrive via the volume mount.
_TRL_JOBS_MOUNT = Path("/mnt/repo/cookbooks/fine_tuning_llms/trl_jobs")
if _TRL_JOBS_MOUNT.is_dir() and str(_TRL_JOBS_MOUNT) not in sys.path:
    sys.path.insert(0, str(_TRL_JOBS_MOUNT))
_LOCAL_DIR = Path(__file__).resolve().parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))

_inference = importlib.import_module("inference")
DEFAULT_SFT_S3_URI = _inference.DEFAULT_SFT_S3_URI
MMLU_RESULTS_S3_URI = _inference.MMLU_RESULTS_S3_URI
MODEL_NAME = _inference.MODEL_NAME
download_s3_prefix = _inference.download_s3_prefix
load_causal_lm = _inference.load_causal_lm
load_tokenizer = _inference.load_tokenizer
upload_json_to_s3 = _inference.upload_json_to_s3

N_SHOTS = 5
DEFAULT_BATCH_SIZE = 8
DEFAULT_MMLU_MAX_NEW_TOKENS = 16
MMLU_TASKS = [
    MMLUTask.COLLEGE_COMPUTER_SCIENCE,
    MMLUTask.PHILOSOPHY,
    MMLUTask.MARKETING,
    MMLUTask.MORAL_SCENARIOS,
    MMLUTask.MORAL_DISPUTES,
]
CHOICE_PATTERN = re.compile(r"\b([ABCD])\b")
CHOICE_LETTERS = ("A", "B", "C", "D")


def extract_choice(text: str) -> str | None:
    """Return the first A/B/C/D in ``text``, or None when none is present."""
    matches = CHOICE_PATTERN.findall(text.upper())
    if not matches:
        return None
    return matches[0]


class CausalLMForMMLU(DeepEvalBaseLLM):
    """Continue a DeepEval MMLU prompt and return the choice letter."""

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        name: str,
        *,
        max_new_tokens: int,
    ) -> None:
        self._causal_lm = model
        self._tokenizer = tokenizer
        self._display_name = name
        self._max_new_tokens = max_new_tokens
        if self._tokenizer.pad_token_id is None and self._tokenizer.eos_token_id:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        super().__init__(model=name)

    def load_model(self, *args: Any, **kwargs: Any) -> Any:
        return self._causal_lm

    def get_model_name(self, *args: Any, **kwargs: Any) -> str:
        return self._display_name

    def generate(self, prompt: str, schema: type[Any] | None = None) -> Any:
        choice = self._choices([prompt])[0]
        if schema is None:
            return choice
        # Returning the schema keeps DeepEval on the prompt that ends in
        # "Answer:". A TypeError would append extra instructions and the
        # small model then continues that sentence instead of the letter.
        return schema(answer=choice)

    async def a_generate(self, prompt: str, schema: type[Any] | None = None) -> Any:
        return self.generate(prompt, schema=schema)

    def batch_generate(
        self,
        prompts: list[str],
        schemas: list[type[Any]] | None = None,
    ) -> list[Any]:
        choices = self._choices(prompts)
        if schemas is None:
            return choices
        if len(schemas) != len(choices):
            raise ValueError("schemas and prompts must be the same length")
        return [
            schema(answer=choice)
            for schema, choice in zip(schemas, choices, strict=True)
        ]

    def _choices(self, prompts: list[str]) -> list[str]:
        texts = self._complete(prompts)
        choices: list[str | None] = [extract_choice(text) for text in texts]
        missing = [index for index, choice in enumerate(choices) if choice is None]
        if missing:
            for index in missing:
                print(f"No choice letter in model output: {texts[index]!r}")
            fallback = self._most_likely_letters([prompts[index] for index in missing])
            for index, letter in zip(missing, fallback, strict=True):
                choices[index] = letter
        return [str(choice) for choice in choices]

    def _choice_token_ids(self) -> dict[str, int]:
        cached = getattr(self, "_choice_token_ids_cache", None)
        if isinstance(cached, dict):
            return cached
        mapping: dict[str, int] = {}
        for letter in CHOICE_LETTERS:
            token_id: int | None = None
            for variant in (f" {letter}", letter):
                token_ids = self._tokenizer.encode(variant, add_special_tokens=False)
                if len(token_ids) == 1:
                    token_id = int(token_ids[0])
                    break
            if token_id is None:
                token_ids = self._tokenizer.encode(letter, add_special_tokens=False)
                token_id = int(token_ids[-1])
            mapping[letter] = token_id
        self._choice_token_ids_cache = mapping
        return mapping

    @torch.inference_mode()
    def _most_likely_letters(self, prompts: list[str]) -> list[str]:
        """Pick A/B/C/D by the next-token probability after the prompt."""
        tokenizer = self._tokenizer
        device = next(self._causal_lm.parameters()).device
        previous_padding_side = tokenizer.padding_side
        tokenizer.padding_side = "left"
        try:
            encoded = tokenizer(prompts, return_tensors="pt", padding=True)
            encoded = {key: value.to(device) for key, value in encoded.items()}
            last_logits = self._causal_lm(**encoded).logits[:, -1, :]
        finally:
            tokenizer.padding_side = previous_padding_side
        token_ids = self._choice_token_ids()
        letters = list(token_ids)
        scores = torch.stack(
            [last_logits[:, token_ids[letter]] for letter in letters],
            dim=-1,
        )
        picked = scores.argmax(dim=-1)
        return [letters[int(index)] for index in picked.tolist()]

    @torch.inference_mode()
    def _complete(self, prompts: list[str]) -> list[str]:
        tokenizer = self._tokenizer
        device = next(self._causal_lm.parameters()).device
        previous_padding_side = tokenizer.padding_side
        tokenizer.padding_side = "left"
        try:
            encoded = tokenizer(prompts, return_tensors="pt", padding=True)
            encoded = {key: value.to(device) for key, value in encoded.items()}
            input_length = encoded["input_ids"].shape[-1]
            output_ids = self._causal_lm.generate(
                **encoded,
                max_new_tokens=self._max_new_tokens,
                min_new_tokens=1,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        finally:
            tokenizer.padding_side = previous_padding_side
        texts: list[str] = []
        for row in output_ids:
            new_tokens = row[input_length:]
            texts.append(tokenizer.decode(new_tokens, skip_special_tokens=True))
        return texts


def _release_gpu_memory() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def score_tasks(
    wrapper: CausalLMForMMLU,
    *,
    n_shots: int,
    batch_size: int,
) -> dict[str, float]:
    """Return subject name to accuracy for each configured MMLU task.

    One ``MMLU`` instance per subject. DeepEval keeps the first subject's
    example questions and reuses them for later subjects in the same instance,
    so a shared instance would score philosophy with computer-science examples.
    """
    scores: dict[str, float] = {}
    for task in MMLU_TASKS:
        benchmark = MMLU(tasks=[task], n_shots=n_shots)
        benchmark.evaluate(model=wrapper, batch_size=batch_size)
        if benchmark.task_scores is None or benchmark.task_scores.empty:
            raise RuntimeError(f"MMLU returned no score for {task.value}")
        score = float(benchmark.task_scores.iloc[0]["Score"])
        scores[task.value] = score
        print(f"{wrapper.get_model_name()} {task.value}: {score:.4f}")
    return scores


def run_mmlu(
    *,
    s3_uri: str = DEFAULT_SFT_S3_URI,
    results_s3_uri: str = MMLU_RESULTS_S3_URI,
    n_shots: int = N_SHOTS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_new_tokens: int = DEFAULT_MMLU_MAX_NEW_TOKENS,
) -> str:
    """Score both models, upload JSON results to S3, and return the URI."""
    print(f"deepeval {deepeval.__version__}")
    print(f"Downloading SFT checkpoint from {s3_uri}")
    checkpoint_dir = download_s3_prefix(s3_uri)
    tokenizer = load_tokenizer(checkpoint_dir)

    print(f"Loading base model {MODEL_NAME}")
    base_model = load_causal_lm(MODEL_NAME)
    base_wrapper = CausalLMForMMLU(
        base_model,
        tokenizer,
        "base",
        max_new_tokens=max_new_tokens,
    )
    base_scores = score_tasks(
        base_wrapper,
        n_shots=n_shots,
        batch_size=batch_size,
    )
    del base_wrapper
    del base_model
    _release_gpu_memory()

    print(f"Loading fine-tuned model from {checkpoint_dir}")
    sft_model = load_causal_lm(checkpoint_dir)
    sft_wrapper = CausalLMForMMLU(
        sft_model,
        tokenizer,
        "fine-tuned",
        max_new_tokens=max_new_tokens,
    )
    fine_tuned_scores = score_tasks(
        sft_wrapper,
        n_shots=n_shots,
        batch_size=batch_size,
    )
    del sft_wrapper
    del sft_model
    _release_gpu_memory()

    payload = {
        "base_model": MODEL_NAME,
        "sft_s3_uri": s3_uri,
        "n_shots": n_shots,
        "batch_size": batch_size,
        "max_new_tokens": max_new_tokens,
        "tasks": [task.value for task in MMLU_TASKS],
        "scores": {
            "base": base_scores,
            "fine_tuned": fine_tuned_scores,
        },
    }
    upload_json_to_s3(payload, results_s3_uri)
    print("Done.")
    return results_s3_uri


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score base and SFT models on five MMLU subjects."
    )
    parser.add_argument(
        "--s3-uri",
        default=DEFAULT_SFT_S3_URI,
        help="S3 URI of the fine-tuned checkpoint directory.",
    )
    parser.add_argument(
        "--results-s3-uri",
        default=MMLU_RESULTS_S3_URI,
        help="S3 URI where the MMLU score JSON will be written.",
    )
    parser.add_argument(
        "--n-shots",
        type=int,
        default=N_SHOTS,
        help="Few-shot examples per question. DeepEval allows at most 5.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Questions generated together on the GPU.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=DEFAULT_MMLU_MAX_NEW_TOKENS,
        help="Maximum new tokens to generate per question.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_mmlu(
        s3_uri=args.s3_uri,
        results_s3_uri=args.results_s3_uri,
        n_shots=args.n_shots,
        batch_size=args.batch_size,
        max_new_tokens=args.max_new_tokens,
    )


if __name__ == "__main__":
    main()
