"""Group Relative Policy Optimization helpers for a tabular softmax policy."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def softmax(logits: Sequence[float]) -> list[float]:
    maximum = max(logits)
    shifted = [math.exp(value - maximum) for value in logits]
    total = sum(shifted)
    return [value / total for value in shifted]


def sample_actions(
    probabilities: Sequence[float],
    group_size: int,
    rng: random.Random,
) -> list[int]:
    actions = list(range(len(probabilities)))
    return [
        rng.choices(actions, weights=list(probabilities), k=1)[0]
        for _ in range(group_size)
    ]


def group_advantages(rewards: Sequence[float], eps: float = 1e-8) -> list[float]:
    """Paper Appendix C.2: A_i = (r_i - mean(r)) / std(r)."""
    n = len(rewards)
    if n == 0:
        return []
    mean = sum(rewards) / n
    variance = sum((reward - mean) ** 2 for reward in rewards) / n
    std = math.sqrt(variance)
    if std < eps:
        return [0.0] * n
    return [(reward - mean) / std for reward in rewards]


def update_logits(
    logits: Sequence[float],
    actions: Sequence[int],
    advantages: Sequence[float],
    *,
    learning_rate: float,
    kl_coefficient: float = 0.0,
    reference_logits: Sequence[float] | None = None,
) -> list[float]:
    """One GRPO-style softmax update averaged over a sampled group."""
    updated = list(logits)
    probabilities = softmax(updated)
    grads = [0.0] * len(updated)
    for action, advantage in zip(actions, advantages, strict=True):
        for index in range(len(updated)):
            indicator = 1.0 if index == action else 0.0
            grads[index] += advantage * (indicator - probabilities[index])
    group_size = max(len(actions), 1)
    for index in range(len(updated)):
        updated[index] += learning_rate * (grads[index] / group_size)

    if kl_coefficient > 0.0 and reference_logits is not None:
        current = softmax(updated)
        reference = softmax(reference_logits)
        for index in range(len(updated)):
            # Push the policy toward the SFT/reference distribution.
            updated[index] -= kl_coefficient * (current[index] - reference[index])
    return updated
