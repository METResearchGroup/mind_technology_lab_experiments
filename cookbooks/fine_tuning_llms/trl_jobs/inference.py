"""Load base and SFT models and run greedy chat generation.

Intended to run on a Hugging Face Job (not the local laptop). The SFT
checkpoint is pulled from S3 onto the job machine's ephemeral disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import boto3
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from shared.aws.constants import DEFAULT_BUCKET, DEFAULT_REGION_NAME
from shared.aws.upload_directory_to_s3 import parse_s3_uri

MODEL_NAME = "Qwen/Qwen2.5-0.5B"
DATASET_NAME = "trl-lib/Capybara"
ARTIFACT_PREFIX = "cookbooks/fine_tuning_llms/trl_jobs"
DEFAULT_SFT_RUN_NAME = "Qwen2.5-0.5B_2026_10_03-22:08:25"
DEFAULT_SFT_S3_URI = f"s3://{DEFAULT_BUCKET}/{ARTIFACT_PREFIX}/{DEFAULT_SFT_RUN_NAME}"

DEFAULT_MAX_NEW_TOKENS = 256
DEFAULT_EVAL_LIMIT = 50
CHECKPOINT_CACHE_ROOT = Path("/tmp/trl_jobs_checkpoints")
EVAL_RESULTS_FILENAME = "comparisons_first_50.json"
EVAL_RESULTS_S3_URI = (
    f"s3://{DEFAULT_BUCKET}/{ARTIFACT_PREFIX}/{DEFAULT_SFT_RUN_NAME}/"
    f"{EVAL_RESULTS_FILENAME}"
)
MMLU_RESULTS_FILENAME = "mmlu_task_scores.json"
MMLU_RESULTS_S3_URI = (
    f"s3://{DEFAULT_BUCKET}/{ARTIFACT_PREFIX}/{DEFAULT_SFT_RUN_NAME}/"
    f"{MMLU_RESULTS_FILENAME}"
)


def default_device_and_dtype() -> tuple[str, torch.dtype]:
    """Pick device and dtype for the current machine."""
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.float32


def download_s3_prefix(
    s3_uri: str,
    *,
    local_dir: Path | None = None,
    region: str = DEFAULT_REGION_NAME,
) -> Path:
    """Download every object under ``s3_uri`` to ``local_dir``.

    Existing files with matching size are skipped so re-runs on a warm job
    machine do not re-fetch the checkpoint.
    """
    bucket, prefix = parse_s3_uri(s3_uri)
    run_name = Path(prefix).name or DEFAULT_SFT_RUN_NAME
    destination = local_dir or (CHECKPOINT_CACHE_ROOT / run_name)
    destination.mkdir(parents=True, exist_ok=True)

    client = boto3.client("s3", region_name=region)
    paginator = client.get_paginator("list_objects_v2")
    downloaded = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.endswith("/"):
                continue
            relative = key[len(prefix) :].lstrip("/")
            if not relative:
                continue
            local_path = destination / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            remote_size = int(item.get("Size", 0))
            if local_path.is_file() and local_path.stat().st_size == remote_size:
                continue
            print(f"Downloading s3://{bucket}/{key} -> {local_path}")
            client.download_file(bucket, key, str(local_path))
            downloaded += 1

    if not any(destination.iterdir()):
        raise FileNotFoundError(f"No objects found under {s3_uri}")
    print(f"Checkpoint ready at {destination} ({downloaded} file(s) fetched)")
    return destination


def load_tokenizer(model_id_or_dir: str | Path) -> AutoTokenizer:
    """Load a tokenizer; trust remote code for Qwen chat templates."""
    return AutoTokenizer.from_pretrained(str(model_id_or_dir), trust_remote_code=True)


def load_causal_lm(
    model_id_or_dir: str | Path,
    *,
    device: str | None = None,
    dtype: torch.dtype | None = None,
) -> AutoModelForCausalLM:
    """Load a causal LM onto the preferred device."""
    resolved_device, resolved_dtype = default_device_and_dtype()
    device = device or resolved_device
    dtype = dtype or resolved_dtype
    model = AutoModelForCausalLM.from_pretrained(
        str(model_id_or_dir),
        dtype=dtype,
        trust_remote_code=True,
    )
    model.to(device)
    model.eval()
    return model


def prompt_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Return chat turns up to the last user message (drop final assistant)."""
    if not messages:
        raise ValueError("Conversation has no messages")
    trimmed = list(messages)
    if trimmed[-1].get("role") == "assistant":
        trimmed = trimmed[:-1]
    if not trimmed or trimmed[-1].get("role") != "user":
        raise ValueError("Conversation must end with a user turn after trimming")
    return [{"role": str(m["role"]), "content": str(m["content"])} for m in trimmed]


def reference_assistant(messages: list[dict[str, Any]]) -> str | None:
    """Return the final assistant turn from the dataset, if present."""
    if messages and messages[-1].get("role") == "assistant":
        return str(messages[-1]["content"])
    return None


def render_prompt(
    tokenizer: AutoTokenizer,
    messages: list[dict[str, str]],
) -> str:
    """Return the exact chat-template text the model is conditioned on."""
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    if not isinstance(prompt, str):
        raise TypeError(f"Expected chat template string, got {type(prompt)}")
    return prompt


@torch.inference_mode()
def generate_reply(
    model: AutoModelForCausalLM,
    tokenizer: AutoTokenizer,
    messages: list[dict[str, str]],
    *,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    prompt_text: str | None = None,
) -> str:
    """Greedy-decode the next assistant turn for ``messages``."""
    device = next(model.parameters()).device
    if prompt_text is None:
        prompt = render_prompt(tokenizer, messages)
    else:
        prompt = prompt_text
    encoded = tokenizer(prompt, return_tensors="pt")
    encoded = {key: value.to(device) for key, value in encoded.items()}
    output_ids = model.generate(
        **encoded,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    new_tokens = output_ids[0, encoded["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def upload_json_to_s3(
    payload: dict[str, Any],
    s3_uri: str,
    *,
    region: str = DEFAULT_REGION_NAME,
) -> str:
    """Serialize ``payload`` as JSON and upload it to ``s3_uri``."""
    bucket, key = parse_s3_uri(s3_uri)
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    client = boto3.client("s3", region_name=region)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    print(f"Uploaded evaluation results to {s3_uri}")
    return s3_uri


def download_s3_object(
    s3_uri: str,
    local_path: Path,
    *,
    region: str = DEFAULT_REGION_NAME,
) -> Path:
    """Download a single S3 object to ``local_path``."""
    bucket, key = parse_s3_uri(s3_uri)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client = boto3.client("s3", region_name=region)
    client.download_file(bucket, key, str(local_path))
    print(f"Downloaded {s3_uri} -> {local_path}")
    return local_path
