#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "torch",
#     "transformers>=4.51.0",
#     "trl>=0.22.0",
#     "peft>=0.15.0",
#     "datasets>=3.0.0",
#     "accelerate>=1.2.0",
#     "openai>=1.40.0",
#     "boto3>=1.35.0",
#     "huggingface_hub>=0.30.0",
#     "trackio",
# ]
# ///
# ruff: noqa: E501

"""Scaled Qwen3-8B Turing-RL job: LoRA SFT warm-start, then GRPO.

Paper (arXiv:2606.19336 / official turing-rl):
  Policy: Qwen/Qwen3-8B with thinking disabled
  Judge:  Qwen/Qwen3.5-397B-A17B via OpenRouter
  Reward: r = (min(s, 5) - 1) / 6, then * 0.9, minus domain length penalty
  GRPO:   LoRA r=64 / alpha=32, lr=1e-5, KL beta=1e-3, G=4, clip=0.2, temp=0.6

This job keeps that recipe but is a short LoRA slice, not 1680 GPU hours.
OPENROUTER_API_KEY is not available here, so the pairwise Likert judge is
gpt-4o-mini (OpenAI) with the paper's 1-7 mapping. Heuristic fallback if the
API fails. Adapters are saved locally and uploaded once at the end.
Mid-run Hub pushes are disabled: Trackio's checkpoint sync crashes on an
empty parquet struct (rank_pattern) and previously killed the job at SFT step 12.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

BASE_MODEL = "Qwen/Qwen3-8B"
PAPER_JUDGE = "Qwen/Qwen3.5-397B-A17B"
DEFAULT_OPENAI_JUDGE = "gpt-4o-mini"
S3_BUCKET = "mind-technology-lab-experiments"
S3_PREFIX = "autoresearch/learning_user_simulators_with_turing_rewards_2026_09_09/"
WORD_RE = re.compile(r"\b[\w']+\b")
QWEN_EMPTY_THINK_PREFILLS = (
    "<think>\n\n</think>\n\n",
    "<think>\n</think>\n\n",
    "<think></think>\n\n",
    "<think>\n\n</think>",
    "<think></think>",
)
ASSISTANT_MARKERS = (
    "i'd be happy to",
    "i would be happy to",
    "as an ai",
    "great question",
    "i can help",
    "here are a few",
    "here are some",
    "let me know if",
    "happy to help",
    "of course!",
    "certainly",
    "i'm here to",
    "let's break this down",
    "you're absolutely right",
)
LORA_TARGETS = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]
CHAT_LENGTH = {
    "r_min": 0.6,
    "r_max": 1.4,
    "lambda_short": 0.40,
    "lambda_long": 0.20,
    "penalty_cap": 0.40,
}
REDDIT_LENGTH = {
    "r_min": 0.8,
    "r_max": 1.1,
    "lambda_short": 0.45,
    "lambda_long": 0.15,
    "penalty_cap": 0.25,
}

TURING_JUDGE_PROMPT = """## Task
You are judging a pairwise Turing test for personalized user simulation.
Decide which candidate was written by the real [HUMAN] user and which was written by an AI imitating that user.

## User History
{user_history}

## Context
{context}

## Response A
{response_a}

## Response B
{response_b}

Score each response 0.0-1.0 on immediate target, human goal, and communication style.
Penalize assistant-like templates, wrong speaker role, and source copying from history.
Compute score_gap = response_b_score - response_a_score, then:
rating 1 if gap <= -2.0; 2 if -2.0 < gap <= -1.0; 3 if -1.0 < gap <= -0.25;
4 if |gap| < 0.25; 5 if 0.25 <= gap < 1.0; 6 if 1.0 <= gap < 2.0; 7 if gap >= 2.0.
1 means A is definitely the real human. 7 means B is definitely the real human.

Return exactly one JSON object with keys rating (integer 1-7) and reason (short string).
"""


@dataclass(frozen=True)
class LengthPenaltyConfig:
    r_min: float
    r_max: float
    lambda_short: float
    lambda_long: float
    penalty_cap: float

    @classmethod
    def for_domain(cls, domain: str) -> LengthPenaltyConfig:
        raw = CHAT_LENGTH if domain == "chat" else REDDIT_LENGTH
        return cls(**raw)


USERS: list[dict[str, Any]] = [
    {
        "name": "Maya",
        "domain": "chat",
        "persona": (
            "Short replies. Skeptical about hype. Uses contractions. Asks one "
            "pointed follow-up instead of listing options."
        ),
        "history": [
            "nah that pitch felt off. who actually uses this day to day?",
            "keep it smaller. i don't want a 12 step plan.",
            "wait, did they even try it with real people?",
        ],
        "prompts": [
            {
                "context": "Assistant: I can walk you through a comprehensive onboarding plan.",
                "target": "skip the plan. did anyone outside the team actually use it?",
            },
            {
                "context": "Assistant: Here are twelve rollout phases with owners and SLAs.",
                "target": "nah that's a deck. who actually uses this day to day?",
            },
            {
                "context": "Assistant: Would you like a detailed comparison of every vendor?",
                "target": "keep it smaller. just tell me who has used it with real people.",
            },
            {
                "context": "Assistant: I can draft a 6-week enablement workshop.",
                "target": "wait, skip the workshop. did they even try it with real people?",
            },
        ],
    },
    {
        "name": "Jordan",
        "domain": "reddit",
        "persona": (
            "Snarky Reddit commenter. Short punchlines. Uses slang. Does not "
            "hedge or write an essay."
        ),
        "history": [
            "lol no. that's the whole post.",
            "bruh they buried the actual mistake in paragraph 4.",
            "wild that people still defend this.",
        ],
        "prompts": [
            {
                "context": "OP: Am I overreacting for leaving after they rewrote my work without asking?",
                "target": "nah you're not overreacting. rewriting it and acting shocked is the tell.",
            },
            {
                "context": "OP: They posted a 'clarification' that ignores the original error.",
                "target": "lol no. that's the whole post. they just buried it again.",
            },
            {
                "context": "OP: People in the thread keep saying I should be grateful they 'improved' it.",
                "target": "wild that people still defend this. bruh they rewrote it.",
            },
            {
                "context": "OP: Manager asked why I'm upset if the rewrite 'sounds better'.",
                "target": "bruh they buried the actual mistake. that's the tell.",
            },
        ],
    },
    {
        "name": "Priya",
        "domain": "chat",
        "persona": (
            "Direct and practical. Talks in first person. Cuts off waffle. "
            "Cares about time cost."
        ),
        "history": [
            "i've got 20 minutes, not a workshop.",
            "if it needs a new account i'm out.",
            "just tell me the one setting that actually changes the output.",
        ],
        "prompts": [
            {
                "context": "Assistant: Would you like a complete tour of every advanced setting?",
                "target": "no tour. which one setting actually changes the output?",
            },
            {
                "context": "Assistant: First create an account, then we can walk through presets.",
                "target": "if it needs a new account i'm out. just the one setting.",
            },
            {
                "context": "Assistant: I can schedule a 90 minute deep dive.",
                "target": "i've got 20 minutes, not a workshop. which control actually matters?",
            },
            {
                "context": "Assistant: There are 40 knobs; I can explain each one in order.",
                "target": "no. just tell me the one setting that actually changes the output.",
            },
        ],
    },
]


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def turing_reward(score: float, *, apply_official_scale: bool = True) -> float:
    clipped = min(float(score), 5.0)
    mapped = (clipped - 1.0) / 6.0
    return mapped * 0.9 if apply_official_scale else mapped


def length_penalty(
    response: str, ground_truth: str, config: LengthPenaltyConfig
) -> float:
    ratio = word_count(response) / max(word_count(ground_truth), 1)
    v_short = max((config.r_min - ratio) / config.r_min, 0.0)
    v_long = max((ratio - config.r_max) / config.r_max, 0.0)
    return min(
        config.lambda_short * v_short + config.lambda_long * v_long, config.penalty_cap
    )


def combine_turing_reward(
    score: float,
    response: str,
    ground_truth: str,
    domain: str,
    *,
    format_score: float = 0.0,
) -> float:
    config = LengthPenaltyConfig.for_domain(domain)
    reward = turing_reward(score, apply_official_scale=True)
    return max(
        0.0, reward + format_score - length_penalty(response, ground_truth, config)
    )


def strip_empty_think_prefill(text: str) -> str:
    for prefill in QWEN_EMPTY_THINK_PREFILLS:
        if text.endswith(prefill):
            return text[: -len(prefill)]
    return text


def system_prompt(user: dict[str, Any]) -> str:
    history = "\n".join(f"- {turn}" for turn in user["history"])
    return (
        "You are simulating one specific human user. Reply as that person, not "
        "as an assistant. Do not offer a plan, a list of options, or a workshop.\n"
        f"Persona: {user['persona']}\n"
        f"Past messages:\n{history}"
    )


def render_chat_prompt(tokenizer: Any, user: dict[str, Any], context: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt(user)},
        {"role": "user", "content": context},
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    return strip_empty_think_prefill(text)


def completion_text(completion: Any) -> str:
    if isinstance(completion, str):
        return completion
    if isinstance(completion, list) and completion:
        last = completion[-1]
        if isinstance(last, dict):
            return str(last.get("content", ""))
        return str(last)
    if isinstance(completion, dict):
        return str(completion.get("content", ""))
    return str(completion)


def generated_is_b(text: str) -> bool:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2 == 0


def parse_rating(raw: str) -> int | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'"rating"\s*:\s*([1-7])', raw)
        return int(match.group(1)) if match else None
    if isinstance(payload, dict):
        value = payload.get("rating", payload.get("score"))
        try:
            rating = int(round(float(value)))
        except (TypeError, ValueError):
            return None
        if 1 <= rating <= 7:
            return rating
    return None


def heuristic_rating(response: str, ground_truth: str) -> int:
    score = 4.0
    lowered = response.lower()
    hits = sum(1 for marker in ASSISTANT_MARKERS if marker in lowered)
    if "1." in response and "2." in response:
        hits += 1
    score -= min(2.5, hits * 0.9)
    gold_len = max(word_count(ground_truth), 1)
    length_gap = abs(word_count(response) - gold_len) / gold_len
    score -= min(1.5, length_gap)
    if any(token in lowered for token in ("nah", "bruh", "lol", "i'm out", "wait")):
        score += 0.8
    return int(max(1, min(7, round(score))))


def openai_pairwise_rating(
    *,
    generated: str,
    ground_truth: str,
    user_history: str,
    context: str,
) -> tuple[int, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return heuristic_rating(generated, ground_truth), "heuristic_no_openai_key"

    gen_is_b = generated_is_b(generated + ground_truth + context)
    response_a = ground_truth if gen_is_b else generated
    response_b = generated if gen_is_b else ground_truth
    prompt = TURING_JUDGE_PROMPT.format(
        user_history=user_history,
        context=context,
        response_a=response_a,
        response_b=response_b,
    )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, max_retries=2, timeout=45.0)
        result = client.chat.completions.create(
            model=os.environ.get("TURING_JUDGE_MODEL", DEFAULT_OPENAI_JUDGE),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        content = result.choices[0].message.content or ""
        rating = parse_rating(content)
        if rating is None:
            return heuristic_rating(generated, ground_truth), "heuristic_parse_failure"
        if not gen_is_b:
            rating = 8 - rating
        return rating, "openai"
    except Exception as exc:  # noqa: BLE001
        print(
            f"[judge] OpenAI failed ({type(exc).__name__}: {exc}); using heuristic",
            flush=True,
        )
        return heuristic_rating(generated, ground_truth), "heuristic_openai_error"


def turing_reward_func(completions: list[Any], **kwargs: Any) -> list[float]:
    ground_truth = (
        kwargs.get("ground_truth") or kwargs.get("target") or [""] * len(completions)
    )
    domain = kwargs.get("domain") or ["chat"] * len(completions)
    user_history = kwargs.get("user_history") or [""] * len(completions)
    context = kwargs.get("context") or [""] * len(completions)
    rewards: list[float] = []
    sources: list[str] = []
    for completion, gold, dom, history, ctx in zip(
        completions, ground_truth, domain, user_history, context, strict=True
    ):
        text = completion_text(completion)
        rating, source = openai_pairwise_rating(
            generated=text,
            ground_truth=str(gold),
            user_history=str(history),
            context=str(ctx),
        )
        reward = combine_turing_reward(float(rating), text, str(gold), str(dom))
        rewards.append(reward)
        sources.append(source)
    print(
        "[reward] "
        f"n={len(rewards)} mean={sum(rewards) / max(len(rewards), 1):.3f} "
        f"sources={{{', '.join(sorted(set(sources)))}}}",
        flush=True,
    )
    return rewards


def build_sft_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for user in USERS:
        for item in user["prompts"]:
            rows.append(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt(user)},
                        {"role": "user", "content": item["context"]},
                        {"role": "assistant", "content": item["target"]},
                    ]
                }
            )
    return rows


def build_grpo_rows(tokenizer: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for user in USERS:
        history = "\n".join(user["history"])
        for item in user["prompts"]:
            rows.append(
                {
                    "prompt": render_chat_prompt(tokenizer, user, item["context"]),
                    "ground_truth": item["target"],
                    "domain": user["domain"],
                    "user_history": history,
                    "context": item["context"],
                    "user_name": user["name"],
                }
            )
    return rows


def filter_supported_kwargs(cls: type, kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        parameters = inspect.signature(cls).parameters
    except (TypeError, ValueError):
        return kwargs
    allowed = set(parameters)
    has_var_keyword = any(
        param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
    )
    # Newer TRL uses processing_class; older uses tokenizer.
    if "processing_class" in allowed and "tokenizer" in kwargs:
        kwargs = {key: value for key, value in kwargs.items() if key != "tokenizer"}
    elif "tokenizer" in allowed:
        kwargs = {
            key: value for key, value in kwargs.items() if key != "processing_class"
        }
    if has_var_keyword:
        return kwargs
    dropped = sorted(key for key in kwargs if key not in allowed)
    if dropped:
        print(
            f"[config] dropping unsupported {cls.__name__} kwargs: {dropped}",
            flush=True,
        )
    return {key: value for key, value in kwargs.items() if key in allowed}


def maybe_upload_s3(local_path: Path, key: str) -> str | None:
    access = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get(
        "AWS_ACCESS_KEY_SECRET"
    )
    if not access or not secret:
        print("[s3] skipped: AWS credentials not set", flush=True)
        return None
    try:
        import boto3

        client = boto3.client(
            "s3",
            aws_access_key_id=access,
            aws_secret_access_key=secret,
        )
        client.upload_file(str(local_path), S3_BUCKET, key)
        uri = f"s3://{S3_BUCKET}/{key}"
        print(f"[s3] uploaded {uri}", flush=True)
        return uri
    except Exception as exc:  # noqa: BLE001
        print(f"[s3] upload failed: {type(exc).__name__}: {exc}", flush=True)
        return None


def metrics_backend() -> str:
    # Trackio checkpoint sync crashes on an empty parquet struct.
    # Trainer logs still print to the Hugging Face Job log.
    return "none"


def upload_adapter(local_dir: Path, repo_id: str) -> None:
    """Upload a saved adapter without Trackio's checkpoint-sync callback."""
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(repo_id, repo_type="model", exist_ok=True)
    api.upload_folder(
        folder_path=str(local_dir),
        repo_id=repo_id,
        repo_type="model",
        commit_message="Upload Turing-RL LoRA adapter",
    )
    print(f"[hub] uploaded {local_dir} -> {repo_id}", flush=True)


def resolve_hub_user() -> str:
    from huggingface_hub import whoami

    info = whoami()
    if isinstance(info, dict):
        name = info.get("name") or info.get("fullname")
        if name:
            return str(name)
    return os.environ.get("HF_USERNAME", "mtorres98")


def run_self_test() -> None:
    assert turing_reward(1.0, apply_official_scale=False) == 0.0
    assert turing_reward(4.0, apply_official_scale=False) == 0.5
    assert turing_reward(5.0, apply_official_scale=True) == (4.0 / 6.0) * 0.9
    assert turing_reward(7.0, apply_official_scale=False) == turing_reward(
        5.0, apply_official_scale=False
    )
    reddit = LengthPenaltyConfig.for_domain("reddit")
    ground = "one two three four five six seven eight nine ten"
    assert (
        length_penalty("one two three four five six seven eight", ground, reddit) == 0.0
    )
    short = length_penalty("one", ground, reddit)
    assert short > 0
    assert combine_turing_reward(7.0, "one", ground, "reddit") >= 0.0
    assert parse_rating('{"rating": 6, "reason": "B sounds like the user"}') == 6
    assert parse_rating('{"score": 3}') == 3
    assert 1 <= heuristic_rating("Great question! I'd be happy to help.", ground) <= 4
    assert len(build_sft_rows()) == 12
    print("self-test ok", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Qwen3-8B Turing-RL SFT + GRPO on HF Jobs"
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--sft-steps", type=int, default=24)
    parser.add_argument("--grpo-steps", type=int, default=8)
    parser.add_argument("--num-generations", type=int, default=4)
    parser.add_argument("--max-completion-length", type=int, default=256)
    parser.add_argument("--lora-rank", type=int, default=64)
    parser.add_argument("--output-dir", default="/tmp/turing-rl-qwen3-8b")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.self_test:
        run_self_test()
        return

    import torch
    from datasets import Dataset
    from huggingface_hub import HfApi, create_repo
    from peft import LoraConfig, TaskType
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import GRPOConfig, GRPOTrainer, SFTConfig, SFTTrainer

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is not available. This script must run on an HF Jobs GPU flavor "
            "(a100-large recommended for Qwen3-8B LoRA GRPO)."
        )

    gpu_name = torch.cuda.get_device_name(0)
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print("=== TURING-RL Qwen3-8B HF JOB ===", flush=True)
    print(f"base_model={args.base_model}", flush=True)
    print(f"paper_judge={PAPER_JUDGE}", flush=True)
    print(
        "job_judge="
        f"{os.environ.get('TURING_JUDGE_MODEL', DEFAULT_OPENAI_JUDGE)} "
        f"(OpenAI; OpenRouter missing)",
        flush=True,
    )
    print(f"torch={torch.__version__} cuda={torch.version.cuda}", flush=True)
    print(f"gpu={gpu_name} mem_gb={gpu_mem:.1f}", flush=True)
    print(
        f"sft_steps={args.sft_steps} grpo_steps={args.grpo_steps} G={args.num_generations}",
        flush=True,
    )

    hub_user = resolve_hub_user()
    sft_repo = f"{hub_user}/turing-rl-qwen3-8b-sft"
    grpo_repo = f"{hub_user}/turing-rl-qwen3-8b-grpo"
    print(f"sft_repo={sft_repo}", flush=True)
    print(f"grpo_repo={grpo_repo}", flush=True)
    for repo_id in (sft_repo, grpo_repo):
        create_repo(repo_id, exist_ok=True, private=False, repo_type="model")

    output_dir = Path(args.output_dir)
    sft_dir = output_dir / "sft"
    grpo_dir = output_dir / "grpo"
    sft_dir.mkdir(parents=True, exist_ok=True)
    grpo_dir.mkdir(parents=True, exist_ok=True)

    print(f"[model] loading tokenizer and {args.base_model}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    print("[model] loading Qwen3-8B weights in bfloat16", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="sdpa",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    print(
        f"[model] loaded {args.base_model} "
        f"params={sum(p.numel() for p in model.parameters()) / 1e9:.2f}B",
        flush=True,
    )

    sft_dataset = Dataset.from_list(build_sft_rows())
    print(f"[data] SFT rows={len(sft_dataset)}", flush=True)

    sft_lora = LoraConfig(
        r=args.lora_rank,
        lora_alpha=128,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=LORA_TARGETS,
    )
    sft_kwargs = {
        "output_dir": str(sft_dir),
        "max_steps": args.sft_steps,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "learning_rate": 2e-4,
        "lr_scheduler_type": "cosine",
        "warmup_ratio": 0.03,
        "logging_steps": 1,
        "save_strategy": "no",
        "bf16": True,
        "gradient_checkpointing": True,
        "gradient_checkpointing_kwargs": {"use_reentrant": False},
        "max_length": 1024,
        "packing": False,
        "assistant_only_loss": True,
        "chat_template_kwargs": {"enable_thinking": False},
        "dataset_kwargs": {"skip_prepare_dataset": False},
        "report_to": metrics_backend(),
        "project": "turing-rl-qwen3-8b",
        "run_name": "sft-qwen3-8b",
        "push_to_hub": False,
        "remove_unused_columns": False,
    }
    sft_args = SFTConfig(**filter_supported_kwargs(SFTConfig, sft_kwargs))
    sft_trainer_kwargs = filter_supported_kwargs(
        SFTTrainer,
        {
            "model": model,
            "args": sft_args,
            "train_dataset": sft_dataset,
            "processing_class": tokenizer,
            "tokenizer": tokenizer,
            "peft_config": sft_lora,
        },
    )
    sft_trainer = SFTTrainer(**sft_trainer_kwargs)
    print("[sft] starting LoRA SFT warm-start", flush=True)
    sft_metrics = sft_trainer.train()
    sft_trainer.save_model(str(sft_dir))
    tokenizer.save_pretrained(str(sft_dir))
    upload_adapter(sft_dir, sft_repo)
    print(f"[sft] done metrics={sft_metrics.metrics}", flush=True)

    del sft_trainer
    del model
    torch.cuda.empty_cache()

    print("[grpo] merging SFT LoRA into Qwen3-8B, then attaching GRPO LoRA", flush=True)
    from peft import PeftModel

    base = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="sdpa",
        trust_remote_code=True,
    )
    if (sft_dir / "adapter_config.json").exists():
        policy = PeftModel.from_pretrained(base, str(sft_dir))
        policy = policy.merge_and_unload()
    else:
        policy = base
    policy.config.use_cache = False

    grpo_dataset = Dataset.from_list(build_grpo_rows(tokenizer))
    print(f"[data] GRPO prompts={len(grpo_dataset)}", flush=True)

    grpo_lora = LoraConfig(
        r=args.lora_rank,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=LORA_TARGETS,
    )
    generation_bs = max(args.num_generations, 4)
    grpo_kwargs = {
        "output_dir": str(grpo_dir),
        "max_steps": args.grpo_steps,
        "per_device_train_batch_size": generation_bs,
        "num_generations": args.num_generations,
        "max_completion_length": args.max_completion_length,
        "max_prompt_length": 768,
        "learning_rate": 1e-5,
        "beta": 1e-3,
        "epsilon": 0.2,
        "temperature": 0.6,
        "top_p": 1.0,
        "logging_steps": 1,
        "save_strategy": "no",
        "bf16": True,
        "gradient_checkpointing": True,
        "gradient_checkpointing_kwargs": {"use_reentrant": False},
        "chat_template_kwargs": {"enable_thinking": False},
        "report_to": metrics_backend(),
        "project": "turing-rl-qwen3-8b",
        "run_name": "grpo-qwen3-8b",
        "push_to_hub": False,
        "remove_unused_columns": False,
        "log_completions": True,
        "num_completions_to_print": 1,
    }
    grpo_args = GRPOConfig(**filter_supported_kwargs(GRPOConfig, grpo_kwargs))
    grpo_trainer_kwargs = filter_supported_kwargs(
        GRPOTrainer,
        {
            "model": policy,
            "reward_funcs": turing_reward_func,
            "args": grpo_args,
            "train_dataset": grpo_dataset,
            "processing_class": tokenizer,
            "tokenizer": tokenizer,
            "peft_config": grpo_lora,
        },
    )
    grpo_trainer = GRPOTrainer(**grpo_trainer_kwargs)
    print("[grpo] starting LoRA GRPO with Turing pairwise reward", flush=True)
    grpo_metrics = grpo_trainer.train()
    grpo_trainer.save_model(str(grpo_dir))
    tokenizer.save_pretrained(str(grpo_dir))
    upload_adapter(grpo_dir, grpo_repo)
    print(f"[grpo] done metrics={grpo_metrics.metrics}", flush=True)

    summary = {
        "paper": "Learning User Simulators with Turing Rewards",
        "arxiv": "2606.19336",
        "base_model": args.base_model,
        "paper_judge": PAPER_JUDGE,
        "job_judge": os.environ.get("TURING_JUDGE_MODEL", DEFAULT_OPENAI_JUDGE),
        "job_judge_reason": "OPENROUTER_API_KEY missing; using OpenAI gpt-4o-mini",
        "gpu": gpu_name,
        "gpu_mem_gb": round(gpu_mem, 2),
        "sft_repo": sft_repo,
        "grpo_repo": grpo_repo,
        "sft_metrics": dict(sft_metrics.metrics),
        "grpo_metrics": dict(grpo_metrics.metrics),
        "scale": {
            "sft_examples": len(sft_dataset),
            "sft_steps": args.sft_steps,
            "grpo_prompts": len(grpo_dataset),
            "grpo_steps": args.grpo_steps,
            "num_generations": args.num_generations,
            "max_completion_length": args.max_completion_length,
            "lora_rank": args.lora_rank,
            "note": "Scaled LoRA slice, not the paper's 1680 GPU-hour run.",
        },
        "finished_at": datetime.now(UTC).isoformat(),
    }
    summary_path = output_dir / "qwen3_8b_job_metrics.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    api = HfApi()
    api.upload_file(
        path_or_fileobj=str(summary_path),
        path_in_repo="qwen3_8b_job_metrics.json",
        repo_id=grpo_repo,
        repo_type="model",
    )
    maybe_upload_s3(summary_path, f"{S3_PREFIX}results/qwen3_8b_job_metrics.json")
    print("=== JOB COMPLETE ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    started = time.time()
    main()
    print(f"[timing] wall_s={time.time() - started:.1f}", flush=True)
