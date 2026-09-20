# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "torch",
#     "transformers>=5.17.0",
#     "accelerate",
#     "numpy",
#     "huggingface_hub",
#     "boto3",
#     "safetensors",
#     "hf_transfer",
# ]
# ///
"""Qwen 3.5 4B user-role vector extraction and steering on Hugging Face Jobs.

Submit from the repository root:

    hf jobs uv run \\
      --flavor l4x1 \\
      --timeout 2h \\
      --secrets HF_TOKEN \\
      --secrets AWS_ACCESS_KEY_ID \\
      --secrets AWS_ACCESS_KEY_SECRET \\
      --env AWS_DEFAULT_REGION=us-east-2 \\
      --env HF_HUB_ENABLE_HF_TRANSFER=1 \\
      --name qwen-user-role-vector \\
      autoresearch/assistant_bias_user_role_vector_2026_09_09/scripts/qwen_role_vector_job.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

MODEL_ID = os.environ.get("QWEN_MODEL_ID", "Qwen/Qwen3.5-4B")
STEER_LAYER_INDEX = int(os.environ.get("STEER_LAYER_INDEX", "11"))
ALPHAS = (-0.3, 0.0, 0.1, 0.2, 0.3)
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "80"))
S3_BUCKET = os.environ.get("S3_BUCKET", "mind-technology-lab-experiments")
S3_PREFIX = os.environ.get(
    "S3_PREFIX", "autoresearch/assistant_bias_user_role_vector_2026_09_09/"
)
S3_REGION = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get(
    "AWS_REGION", "us-east-2"
)
HUB_DATASET = os.environ.get("HUB_DATASET", "")

PROMPT_VARIANTS = (
    "transcript_analysis",
    "role_simulation",
    "dialogue_participant",
)
_INTROS = {
    "transcript_analysis": (
        "You are analyzing the following dialogue from the perspective of the {role}."
    ),
    "role_simulation": (
        "You are simulating the role of the {role} in the following dialogue."
    ),
    "dialogue_participant": "You are the {role} in the following dialogue.",
}
_REFLECTION_QUESTION = (
    "Instruction: Write a brief reflection from the {role}'s perspective "
    "in one paragraph. Write exactly one paragraph."
)
USER_SIMULATOR_INSTRUCTION = (
    "You are simulating a human user talking to an AI assistant. "
    "Write only the user's first message. Do not write the assistant's reply. "
    "Do not mention that you are a simulator. Goal: {goal}"
)

_CONTRACTIONS = re.compile(
    r"\b(i'm|i've|i'd|i'll|don't|can't|won't|isn't|aren't|wasn't|"
    r"weren't|hasn't|haven't|hadn't|doesn't|didn't|wouldn't|couldn't|"
    r"shouldn't|that's|it's|what's|how's|let's|gonna|wanna|gotta)\b",
    re.IGNORECASE,
)
_FORMAL = re.compile(
    r"\b(please|kindly|assist|could you|would you|furthermore|"
    r"therefore|regarding|ensure|subsequently)\b",
    re.IGNORECASE,
)
_DETAIL = re.compile(
    r"\b(order|because|including|step-by-step|specifically|"
    r"first|next|finally|constraints?)\b",
    re.IGNORECASE,
)

DIALOGUES: list[dict[str, Any]] = [
    {
        "dialogue_id": "furniture",
        "topic": "how_to_advice",
        "turns": [
            {
                "role": "user",
                "content": "I bought a flat-pack desk and the instructions are terrible.",
            },
            {
                "role": "assistant",
                "content": (
                    "I can walk you through it. Start by laying out every panel "
                    "and bag of screws and matching them to the parts list."
                ),
            },
            {
                "role": "user",
                "content": "Okay, I have two identical side panels and a bag labeled C.",
            },
            {
                "role": "assistant",
                "content": (
                    "Bag C is usually the cam locks. Attach the side panels to "
                    "the desktop first, cams facing inward, before you add the legs."
                ),
            },
        ],
    },
    {
        "dialogue_id": "headphones",
        "topic": "purchasable_products",
        "turns": [
            {
                "role": "user",
                "content": "Need noise-canceling headphones for a long-haul flight.",
            },
            {
                "role": "assistant",
                "content": (
                    "Look at comfort, battery life, and how strong the ANC is at "
                    "engine rumble frequencies. A few popular options sit around $200-350."
                ),
            },
            {
                "role": "user",
                "content": "I don't want to spend more than $250 and I wear glasses.",
            },
            {
                "role": "assistant",
                "content": (
                    "Then prioritize padding that doesn't clamp the temples. "
                    "Several mid-range models last over 20 hours and fold into a case."
                ),
            },
        ],
    },
    {
        "dialogue_id": "invite",
        "topic": "personal_writing_or_communication",
        "turns": [
            {
                "role": "user",
                "content": "I need to decline a dinner invite without sounding rude.",
            },
            {
                "role": "assistant",
                "content": (
                    "Keep it short: thank them, say you cannot make it, and offer "
                    "another time if you mean it."
                ),
            },
            {
                "role": "user",
                "content": "It's a coworker I like. I just already have plans.",
            },
            {
                "role": "assistant",
                "content": (
                    "Say you appreciate the invite and already have a commitment "
                    "that night. Suggest coffee later in the week."
                ),
            },
        ],
    },
    {
        "dialogue_id": "return",
        "topic": "purchasable_products",
        "turns": [
            {
                "role": "user",
                "content": "The zipper on the jacket I ordered last week already broke.",
            },
            {
                "role": "assistant",
                "content": (
                    "Most shops will take a defective zipper as a return or "
                    "replacement. Do you still have the order number?"
                ),
            },
            {"role": "user", "content": "Yes, 48291. I just want a refund."},
            {
                "role": "assistant",
                "content": (
                    "Write that the zipper failed after a few uses, attach a photo, "
                    "and ask for a refund to the original payment method."
                ),
            },
        ],
    },
    {
        "dialogue_id": "algebra",
        "topic": "tutoring_or_teaching",
        "turns": [
            {
                "role": "user",
                "content": "I moved the x terms to the left and I think I dropped a sign.",
            },
            {
                "role": "assistant",
                "content": (
                    "Show me the line before and after the move. A missing minus "
                    "is the usual failure when both sides have x."
                ),
            },
            {
                "role": "user",
                "content": "I had 3x - 5 = 1 - 2x and I wrote 3x + 2x = 1 + 5.",
            },
            {
                "role": "assistant",
                "content": (
                    "That is correct: adding 2x and adding 5 to both sides. "
                    "Next divide 5x = 6."
                ),
            },
        ],
    },
    {
        "dialogue_id": "debug",
        "topic": "computer_programming",
        "turns": [
            {
                "role": "user",
                "content": "My Python script crashes with a KeyError on 'user_id'.",
            },
            {
                "role": "assistant",
                "content": (
                    "Print the dict keys just before the lookup. Either the API "
                    "renamed the field or you are parsing a nested object."
                ),
            },
            {
                "role": "user",
                "content": "It is nested under data.profile. The top level has status.",
            },
            {
                "role": "assistant",
                "content": (
                    "Then read payload['data']['profile']['user_id'] after you "
                    "check that status is ok."
                ),
            },
        ],
    },
    {
        "dialogue_id": "recipe",
        "topic": "cooking_and_recipes",
        "turns": [
            {
                "role": "user",
                "content": "I want a weeknight pasta that uses only pantry stuff.",
            },
            {
                "role": "assistant",
                "content": (
                    "Garlic, olive oil, chili flakes, and pasta water make a "
                    "sauce in the time it takes the noodles to cook."
                ),
            },
            {
                "role": "user",
                "content": "I have a can of tomatoes and some parmesan too.",
            },
            {
                "role": "assistant",
                "content": (
                    "Simmer the tomatoes with garlic for ten minutes, toss with "
                    "pasta, and finish with cheese and pasta water."
                ),
            },
        ],
    },
    {
        "dialogue_id": "chitchat",
        "topic": "greetings_and_chitchat",
        "turns": [
            {"role": "user", "content": "Hey, just killing time before a meeting."},
            {
                "role": "assistant",
                "content": "Happy to chat. What is the meeting about, or do you want a distraction?",
            },
            {
                "role": "user",
                "content": "It's a status update. I already sent the slides.",
            },
            {
                "role": "assistant",
                "content": (
                    "Then you are in good shape. If you want, we can brainstorm "
                    "one sentence that summarizes the week."
                ),
            },
        ],
    },
]

USER_GOALS = (
    {"id": "furniture", "goal": "Assemble a piece of flat-pack furniture"},
    {"id": "headphones", "goal": "Choose noise-canceling headphones for flights"},
    {"id": "invite", "goal": "Decline a dinner invitation politely"},
    {"id": "return", "goal": "Return a jacket with a broken zipper"},
    {"id": "algebra", "goal": "Ask a tutor about a confusing algebra step"},
)


def format_dialogue_text(turns: list[dict[str, str]]) -> str:
    lines = [f"{turn['role'].capitalize()}: {turn['content']}" for turn in turns]
    return " ".join(lines)


def build_reflection_prompt(role: str, dialogue_text: str, variant: str) -> str:
    intro = _INTROS[variant].format(role=role)
    question = _REFLECTION_QUESTION.format(role=role)
    return f"{intro} Dialogue: {dialogue_text} {question}"


def extract_user_role_vector(user: np.ndarray, assistant: np.ndarray) -> np.ndarray:
    if user.shape != assistant.shape:
        raise ValueError("user and assistant activations must share a shape")
    return np.mean(user - assistant, axis=0)


def unit_vector(vector: np.ndarray) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float64).reshape(-1)
    norm = float(np.linalg.norm(array))
    if norm == 0.0:
        raise ValueError("cannot normalize a zero vector")
    return array / norm


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=np.float64).reshape(-1)
    b = np.asarray(right, dtype=np.float64).reshape(-1)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def project_onto_direction(hidden: np.ndarray, role_vector: np.ndarray) -> float:
    return float(np.dot(np.asarray(hidden, dtype=np.float64).reshape(-1), unit_vector(role_vector)))


def clip_score(value: float) -> float:
    return float(min(5.0, max(1.0, value)))


def score_user_likeness(message: str) -> dict[str, float | int]:
    text = message.strip()
    words = re.findall(r"[A-Za-z0-9']+", text)
    n_words = max(len(words), 1)
    brevity = clip_score(6.2 - 0.09 * n_words)
    contraction_hits = len(_CONTRACTIONS.findall(text))
    formal_hits = len(_FORMAL.findall(text))
    starts_lower = 1.0 if text[:1].islower() else 0.0
    has_question_only = 1.0 if text.endswith("?") and n_words <= 12 else 0.0
    informality = clip_score(
        2.2
        + 0.7 * contraction_hits
        + 0.6 * starts_lower
        + 0.5 * has_question_only
        - 0.45 * formal_hits
    )
    detail_hits = len(_DETAIL.findall(text))
    comma_count = text.count(",")
    pacing = clip_score(4.8 - 0.35 * detail_hits - 0.15 * comma_count - 0.03 * n_words)
    mean = (brevity + informality + pacing) / 3.0
    return {
        "brevity": brevity,
        "informality": informality,
        "information_pacing": pacing,
        "mean": mean,
        "word_count": len(words),
    }


def aws_secret() -> str | None:
    return (
        os.environ.get("AWS_SECRET_ACCESS_KEY")
        or os.environ.get("AWS_ACCESS_KEY_SECRET")
        or os.environ.get("LAB_AWS_ACCESS_KEY_SECRET")
    )


def aws_key() -> str | None:
    return os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("LAB_AWS_ACCESS_KEY_ID")


def pair_role_activations(
    records: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    keyed = {
        (item["dialogue_id"], item["variant"], item["role"]): item for item in records
    }
    user_rows: list[np.ndarray] = []
    assistant_rows: list[np.ndarray] = []
    pairs = {
        (dialogue_id, variant)
        for dialogue_id, variant, role in keyed
        if role in {"user", "assistant"}
    }
    for dialogue_id, variant in sorted(pairs, key=lambda item: (str(item[0]), str(item[1]))):
        user = keyed.get((dialogue_id, variant, "user"))
        assistant = keyed.get((dialogue_id, variant, "assistant"))
        if user is None or assistant is None:
            continue
        user_rows.append(np.asarray(user["activation"], dtype=np.float64))
        assistant_rows.append(np.asarray(assistant["activation"], dtype=np.float64))
    if not user_rows:
        raise ValueError("no paired user/assistant activations")
    return np.stack(user_rows), np.stack(assistant_rows)


def average_role_activations(
    records: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray]:
    grouped: dict[tuple[Any, Any], list[np.ndarray]] = defaultdict(list)
    for item in records:
        grouped[(item["dialogue_id"], item["role"])].append(
            np.asarray(item["activation"], dtype=np.float64)
        )
    dialogue_ids = sorted(
        {dialogue_id for dialogue_id, role in grouped if role in {"user", "assistant"}},
        key=str,
    )
    user_rows: list[np.ndarray] = []
    assistant_rows: list[np.ndarray] = []
    for dialogue_id in dialogue_ids:
        user_list = grouped.get((dialogue_id, "user"))
        assistant_list = grouped.get((dialogue_id, "assistant"))
        if not user_list or not assistant_list:
            continue
        user_rows.append(np.mean(np.stack(user_list), axis=0))
        assistant_rows.append(np.mean(np.stack(assistant_list), axis=0))
    if not user_rows:
        raise ValueError("no dialogues with both roles")
    return np.stack(user_rows), np.stack(assistant_rows)


def mean_style_by_alpha(rows: list[dict[str, Any]]) -> list[dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["alpha"])].append(row)
    summary = []
    for alpha in sorted(grouped, key=float):
        items = grouped[alpha]
        n = max(len(items), 1)
        summary.append(
            {
                "alpha": float(alpha),
                "brevity": sum(float(item["brevity"]) for item in items) / n,
                "informality": sum(float(item["informality"]) for item in items) / n,
                "information_pacing": sum(float(item["information_pacing"]) for item in items)
                / n,
                "mean": sum(float(item["mean"]) for item in items) / n,
                "word_count": sum(float(item["word_count"]) for item in items) / n,
            }
        )
    return summary


def unwrap_hidden(output: Any) -> Any:
    if isinstance(output, tuple):
        return output[0], output[1:]
    return output, None


def wrap_hidden(hidden: Any, rest: Any) -> Any:
    if rest is None:
        return hidden
    return (hidden, *rest)


def find_text_layers(model: Any) -> tuple[str, Any]:
    import torch.nn as nn

    matches: list[tuple[str, Any]] = []
    for name, module in model.named_modules():
        if isinstance(module, nn.ModuleList) and len(module) >= 16:
            matches.append((name, module))
    if not matches:
        raise RuntimeError("could not find a decoder ModuleList on the model")
    matches.sort(
        key=lambda item: (
            0 if len(item[1]) == 32 else 1,
            0 if "language" in item[0] else 1,
            0 if item[0].endswith("layers") else 1,
            -len(item[1]),
            len(item[0]),
        )
    )
    name, module = matches[0]
    print(f"Using decoder layers at {name!r} with {len(module)} blocks", flush=True)
    return name, module


def tokenize_chat(tokenizer: Any, user_text: str, device: Any) -> dict[str, Any]:
    messages = [{"role": "user", "content": user_text}]
    kwargs = {
        "add_generation_prompt": True,
        "tokenize": True,
        "return_tensors": "pt",
        "return_dict": True,
        "enable_thinking": False,
    }
    try:
        encoded = tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        encoded = tokenizer.apply_chat_template(messages, **kwargs)
    if hasattr(encoded, "keys"):
        batch = {}
        for key, value in encoded.items():
            if key not in {"input_ids", "attention_mask"}:
                continue
            batch[key] = value.to(device) if hasattr(value, "to") else value
        return batch
    return {"input_ids": encoded.to(device)}


def last_token_index(attention_mask: Any) -> int:
    return int(attention_mask[0].sum().item()) - 1


def load_model(model_id: str) -> tuple[Any, Any, str]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading {model_id}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if getattr(tokenizer, "pad_token_id", None) is None:
        tokenizer.pad_token = tokenizer.eos_token
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            dtype=torch.bfloat16,
            device_map="auto",
        )
        kind = "causal_lm"
    except Exception as exc:
        print(f"CausalLM load failed ({exc!r}); trying conditional generation", flush=True)
        from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

        processor = AutoProcessor.from_pretrained(model_id)
        model = Qwen3_5ForConditionalGeneration.from_pretrained(
            model_id,
            dtype=torch.bfloat16,
            device_map="auto",
        )
        tokenizer = getattr(processor, "tokenizer", tokenizer)
        kind = "conditional"
    model.eval()
    return model, tokenizer, kind


def capture_last_hidden(
    model: Any,
    layers: Any,
    layer_index: int,
    inputs: dict[str, Any],
) -> np.ndarray:
    import torch

    captured: dict[str, Any] = {}

    def hook(_module: Any, _inputs: Any, output: Any) -> Any:
        hidden, _rest = unwrap_hidden(output)
        captured["h"] = hidden.detach()
        return output

    handle = layers[layer_index].register_forward_hook(hook)
    try:
        with torch.inference_mode():
            model(**inputs, use_cache=False)
    finally:
        handle.remove()
    if "h" not in captured:
        raise RuntimeError("layer hook did not fire")
    hidden = captured["h"]
    index = last_token_index(inputs["attention_mask"]) if "attention_mask" in inputs else hidden.shape[1] - 1
    return hidden[0, index, :].float().cpu().numpy()


def generate_steered(
    model: Any,
    tokenizer: Any,
    layers: Any,
    layer_index: int,
    inputs: dict[str, Any],
    direction: np.ndarray,
    alpha: float,
    max_new_tokens: int,
) -> str:
    import torch

    prompt_len = int(inputs["input_ids"].shape[1])
    vec = torch.tensor(unit_vector(direction), device=inputs["input_ids"].device)
    handle = None
    if alpha != 0.0:

        def hook(_module: Any, _inputs: Any, output: Any) -> Any:
            hidden, rest = unwrap_hidden(output)
            if not torch.is_tensor(hidden) or hidden.ndim != 3:
                return output
            local = vec.to(device=hidden.device, dtype=hidden.dtype)
            norms = torch.linalg.vector_norm(hidden, dim=-1, keepdim=True).clamp_min(1e-6)
            steered = hidden + (alpha * norms) * local
            return wrap_hidden(steered, rest)

        handle = layers[layer_index].register_forward_hook(hook)
    try:
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                use_cache=True,
            )
    finally:
        if handle is not None:
            handle.remove()
    new_tokens = generated[0, prompt_len:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return text.strip()


def persist_payload(payload: dict[str, Any]) -> dict[str, str | None]:
    out_dir = Path("/tmp/qwen_role_vector")
    out_dir.mkdir(parents=True, exist_ok=True)
    local_path = out_dir / "qwen_run.json"
    local_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {local_path}", flush=True)

    destinations: dict[str, str | None] = {
        "local_path": str(local_path),
        "hub_url": None,
        "s3_uri": None,
    }
    token = os.environ.get("HF_TOKEN")
    if token:
        from huggingface_hub import HfApi

        api = HfApi(token=token)
        username = api.whoami()["name"]
        repo_id = HUB_DATASET or f"{username}/assistant-bias-user-role-vector-qwen-run"
        api.create_repo(repo_id, repo_type="dataset", exist_ok=True, private=True)
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo="qwen_run.json",
            repo_id=repo_id,
            repo_type="dataset",
        )
        destinations["hub_url"] = f"https://huggingface.co/datasets/{repo_id}/blob/main/qwen_run.json"
        print(f"Uploaded Hub dataset {repo_id}", flush=True)
    else:
        print("HF_TOKEN missing; skipping Hub upload", flush=True)

    key = aws_key()
    secret = aws_secret()
    if key and secret:
        import boto3

        s3 = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
        )
        object_key = f"{S3_PREFIX.rstrip('/')}/qwen_run.json"
        s3.upload_file(str(local_path), S3_BUCKET, object_key)
        destinations["s3_uri"] = f"s3://{S3_BUCKET}/{object_key}"
        print(f"Uploaded {destinations['s3_uri']}", flush=True)
    else:
        print(
            "AWS keys missing; skipping S3 upload. "
            "Need AWS_ACCESS_KEY_ID plus AWS_ACCESS_KEY_SECRET "
            "(or LAB_AWS_ACCESS_KEY_ID / LAB_AWS_ACCESS_KEY_SECRET).",
            flush=True,
        )
    return destinations


def run() -> dict[str, Any]:
    import torch

    started = time.time()
    if not torch.cuda.is_available():
        raise SystemExit(
            f"CUDA is required. torch={torch.__version__} cuda={torch.version.cuda}"
        )
    print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)
    print(f"torch={torch.__version__}", flush=True)

    model, tokenizer, kind = load_model(MODEL_ID)
    device = next(model.parameters()).device
    layer_name, layers = find_text_layers(model)
    if STEER_LAYER_INDEX < 0 or STEER_LAYER_INDEX >= len(layers):
        raise SystemExit(f"layer {STEER_LAYER_INDEX} out of range 0..{len(layers) - 1}")
    print(f"Steering layer {STEER_LAYER_INDEX}/{len(layers)}", flush=True)

    records: list[dict[str, Any]] = []
    for dialogue in DIALOGUES:
        dialogue_text = format_dialogue_text(dialogue["turns"])
        for variant in PROMPT_VARIANTS:
            for role in ("user", "assistant"):
                prompt = build_reflection_prompt(role, dialogue_text, variant)
                inputs = tokenize_chat(tokenizer, prompt, device)
                activation = capture_last_hidden(
                    model, layers, STEER_LAYER_INDEX, inputs
                )
                records.append(
                    {
                        "dialogue_id": dialogue["dialogue_id"],
                        "topic": dialogue["topic"],
                        "variant": variant,
                        "role": role,
                        "n_prompt_tokens": int(inputs["input_ids"].shape[1]),
                        "activation": activation,
                    }
                )
                print(
                    f"activation {dialogue['dialogue_id']} {variant} {role} "
                    f"tokens={inputs['input_ids'].shape[1]}",
                    flush=True,
                )

    user_avg, assistant_avg = average_role_activations(records)
    vector = extract_user_role_vector(user_avg, assistant_avg)
    user_proj = float(np.mean([project_onto_direction(row, vector) for row in user_avg]))
    assistant_proj = float(
        np.mean([project_onto_direction(row, vector) for row in assistant_avg])
    )
    print(
        f"vector_norm={float(np.linalg.norm(vector)):.4f} "
        f"user_proj={user_proj:.4f} assistant_proj={assistant_proj:.4f}",
        flush=True,
    )

    steered_rows: list[dict[str, Any]] = []
    for goal in USER_GOALS:
        prompt = USER_SIMULATOR_INSTRUCTION.format(goal=goal["goal"])
        inputs = tokenize_chat(tokenizer, prompt, device)
        for alpha in ALPHAS:
            text = generate_steered(
                model,
                tokenizer,
                layers,
                STEER_LAYER_INDEX,
                inputs,
                vector,
                alpha,
                MAX_NEW_TOKENS,
            )
            scores = score_user_likeness(text)
            row = {
                "goal_id": goal["id"],
                "goal": goal["goal"],
                "alpha": alpha,
                "text": text,
                **scores,
            }
            steered_rows.append(row)
            print(
                f"steer {goal['id']} alpha={alpha} mean={scores['mean']:.2f} "
                f"words={scores['word_count']}",
                flush=True,
            )
            print(f"TEXT {goal['id']} {alpha}: {text[:240]!r}", flush=True)

    style_summary = mean_style_by_alpha(steered_rows)
    payload = {
        "kind": "qwen_role_vector_job",
        "status": "ok",
        "model": MODEL_ID,
        "model_load": kind,
        "layer_index": STEER_LAYER_INDEX,
        "layer_module": layer_name,
        "n_layers": len(layers),
        "n_dialogues": len(DIALOGUES),
        "n_prompt_variants": len(PROMPT_VARIANTS),
        "n_pairs": int(user_avg.shape[0]),
        "hidden_size": int(vector.shape[0]),
        "vector_norm": float(np.linalg.norm(vector)),
        "user_mean_projection": user_proj,
        "assistant_mean_projection": assistant_proj,
        "cosine_user_minus_assistant": cosine_similarity(
            np.mean(user_avg, axis=0), np.mean(assistant_avg, axis=0)
        ),
        "gpu": torch.cuda.get_device_name(0),
        "job_id": os.environ.get("JOB_ID"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": time.time() - started,
        "steering": [
            {key: value for key, value in row.items() if key != "activation"}
            for row in steered_rows
        ],
        "mean_user_likeness_by_alpha": style_summary,
        "notes": [
            "Activations are the residual stream at the last prompt token on the chosen layer.",
            "That token is the first-response-token position after add_generation_prompt.",
            "Thinking is disabled so the first generated tokens are the visible reply.",
            "Style scores are the lexical stand-in, not GPT-5 Mini.",
            "Dialogues are 8 hand-crafted chats, not LMSYS-Chat-1M.",
        ],
    }
    destinations = persist_payload(payload)
    payload["hub_url"] = destinations["hub_url"]
    payload["s3_uri"] = destinations["s3_uri"]
    if destinations["hub_url"] or destinations["s3_uri"]:
        persist_payload(payload)
    print(json.dumps({
        "status": "ok",
        "vector_norm": payload["vector_norm"],
        "user_mean_projection": user_proj,
        "assistant_mean_projection": assistant_proj,
        "style": style_summary,
        "hub_url": destinations["hub_url"],
        "s3_uri": destinations["s3_uri"],
        "elapsed_sec": payload["elapsed_sec"],
    }, indent=2), flush=True)
    print("VERDICT: ok", flush=True)
    return payload


def main() -> None:
    try:
        run()
    except Exception:
        traceback.print_exc()
        print("VERDICT: error", flush=True)
        raise


if __name__ == "__main__":
    main()
