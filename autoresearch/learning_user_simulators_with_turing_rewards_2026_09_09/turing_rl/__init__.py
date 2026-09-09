"""Bare-minimum Turing-RL replica for dummy user-simulator data."""

from turing_rl.grpo import group_advantages, softmax, update_logits
from turing_rl.rewards import (
    LengthPenaltyConfig,
    clip_turing_judge_score,
    combine_turing_reward,
    length_penalty,
    turing_reward,
    word_count,
)

__all__ = [
    "LengthPenaltyConfig",
    "clip_turing_judge_score",
    "combine_turing_reward",
    "group_advantages",
    "length_penalty",
    "softmax",
    "turing_reward",
    "update_logits",
    "word_count",
]
