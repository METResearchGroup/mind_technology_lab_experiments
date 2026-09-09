"""Turing, similarity, log-probability, and length-penalty rewards.

Formulas follow Wang et al., Learning User Simulators with Turing Rewards
(arXiv:2606.19336) and the official turing-rl reward helpers.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

WORD_RE = re.compile(r"\b[\w']+\b")
CONTENT_RE = re.compile(r"[a-z0-9']+")

# Paper §2.2: cap the Likert score at 5 before mapping onto [0, 1].
TURING_JUDGE_SCORE_CLIP_MAX = 5.0
TURING_SCORE_MIN = 1.0
TURING_SCORE_MAX = 7.0
TURING_DENOMINATOR = 6.0

# Official training code multiplies the paper mapping by 0.9.
TURING_RAW_REWARD_SCALE = 0.9

# Paper Appendix C.3 / Table 7.
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
        return cls(
            r_min=raw["r_min"],
            r_max=raw["r_max"],
            lambda_short=raw["lambda_short"],
            lambda_long=raw["lambda_long"],
            penalty_cap=raw["penalty_cap"],
        )


def word_count(text: str) -> int:
    """Count words the same way the official reward helper does."""
    return len(WORD_RE.findall(text or ""))


def content_tokens(text: str) -> list[str]:
    """Lowercased content tokens used by the dummy similarity judge."""
    return CONTENT_RE.findall((text or "").lower())


def clip_turing_judge_score(score: float) -> float:
    """Clip a 1-7 Likert score at 5 to reduce reward hacking."""
    return min(float(score), TURING_JUDGE_SCORE_CLIP_MAX)


def turing_reward(score: float, *, apply_official_scale: bool = False) -> float:
    """Map a Likert Turing score onto [0, 1].

    Paper §2.2: r = (min(s, 5) - 1) / 6.
    The official trainer then multiplies by 0.9.
    """
    clipped = clip_turing_judge_score(score)
    mapped = (clipped - TURING_SCORE_MIN) / TURING_DENOMINATOR
    if apply_official_scale:
        return mapped * TURING_RAW_REWARD_SCALE
    return mapped


def length_ratio(response: str, ground_truth: str) -> float:
    generated = word_count(response)
    human = max(word_count(ground_truth), 1)
    return generated / human


def length_penalty(
    response: str, ground_truth: str, config: LengthPenaltyConfig
) -> float:
    """Paper Appendix C.3 length penalty, capped per domain."""
    ratio = length_ratio(response, ground_truth)
    v_short = max((config.r_min - ratio) / config.r_min, 0.0)
    v_long = max((ratio - config.r_max) / config.r_max, 0.0)
    raw = config.lambda_short * v_short + config.lambda_long * v_long
    return min(raw, config.penalty_cap)


def combine_turing_reward(
    score: float,
    response: str,
    ground_truth: str,
    config: LengthPenaltyConfig,
    *,
    format_score: float = 0.0,
    apply_official_scale: bool = False,
) -> float:
    """Final training reward: Turing mapping plus format, minus length penalty."""
    reward = turing_reward(score, apply_official_scale=apply_official_scale)
    penalty = length_penalty(response, ground_truth, config)
    return max(0.0, reward + format_score - penalty)


def token_f1(response: str, ground_truth: str) -> float:
    """Content-token F1 used as the dummy Sim-RL reward in [0, 1]."""
    pred = set(content_tokens(response))
    gold = set(content_tokens(ground_truth))
    if not pred and not gold:
        return 1.0
    if not pred or not gold:
        return 0.0
    overlap = len(pred & gold)
    precision = overlap / len(pred)
    recall = overlap / len(gold)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def mean_gt_logprob(response: str, ground_truth: str) -> float:
    """Mean log unigram probability of ground-truth tokens under the response.

    This is a dummy stand-in for the paper's r_logprob(z) =
    (1/|y*| ) log p_theta(y*| x, u, z).
    """
    response_tokens = content_tokens(response)
    gold_tokens = content_tokens(ground_truth)
    if not gold_tokens:
        return 0.0
    if not response_tokens:
        return -8.0
    counts: dict[str, int] = {}
    for token in response_tokens:
        counts[token] = counts.get(token, 0) + 1
    vocab = len(counts)
    total = len(response_tokens)
    log_mass = 0.0
    for token in gold_tokens:
        # Add-1 smoothing over the response vocabulary plus an UNK bucket.
        prob = (counts.get(token, 0) + 1.0) / (total + vocab + 1.0)
        log_mass += math.log(prob)
    mean = log_mass / len(gold_tokens)
    return max(-8.0, min(0.0, mean))
