"""Dummy Turing and similarity judges for the toy replica.

The paper uses Qwen3.5-397B-A17B as a pairwise Likert judge. This replica
uses a transparent heuristic so the reward math can run without a GPU.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from turing_rl.rewards import content_tokens, token_f1, word_count

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
)
HEDGES = ("perhaps", "it might", "it could", "one might", "generally speaking")
FIRST_PERSON = re.compile(r"\b(i|i'm|i've|my|me)\b", re.I)
CONTRACTION = re.compile(r"\b\w+'\w+\b")


@dataclass(frozen=True)
class StyleProfile:
    mean_words: float
    contraction_rate: float
    first_person_rate: float
    hedge_rate: float
    quirks: tuple[str, ...]


def profile_text(text: str, quirks: tuple[str, ...] = ()) -> StyleProfile:
    tokens = content_tokens(text)
    n = max(len(tokens), 1)
    return StyleProfile(
        mean_words=float(word_count(text)),
        contraction_rate=len(CONTRACTION.findall(text)) / n,
        first_person_rate=len(FIRST_PERSON.findall(text)) / n,
        hedge_rate=sum(text.lower().count(word) for word in HEDGES) / n,
        quirks=quirks,
    )


def _assistant_penalty(text: str) -> float:
    lowered = text.lower()
    hits = sum(1 for marker in ASSISTANT_MARKERS if marker in lowered)
    if "1." in text and "2." in text:
        hits += 1
    return min(2.5, hits * 0.9)


def _quirk_bonus(text: str, quirks: tuple[str, ...]) -> float:
    lowered = text.lower()
    if not quirks:
        return 0.0
    hits = sum(1 for quirk in quirks if quirk.lower() in lowered)
    return min(1.5, hits * 0.75)


def turing_likert(
    response: str,
    ground_truth: str,
    history_profile: StyleProfile,
) -> float:
    """Return a 1-7 score: 7 means the model reply looks more like the user."""
    score = 4.0
    response_profile = profile_text(response, history_profile.quirks)

    length_gap = abs(response_profile.mean_words - history_profile.mean_words)
    score -= min(1.5, length_gap / max(history_profile.mean_words, 1.0))

    contraction_gap = abs(
        response_profile.contraction_rate - history_profile.contraction_rate
    )
    person_gap = abs(
        response_profile.first_person_rate - history_profile.first_person_rate
    )
    score -= 1.2 * contraction_gap
    score -= 0.8 * person_gap
    score -= 0.6 * abs(response_profile.hedge_rate - history_profile.hedge_rate)
    score -= _assistant_penalty(response)
    score += _quirk_bonus(response, history_profile.quirks)

    # Being indistinguishable is not the same as copying the ground truth, so
    # exact overlap only gets a small bump.
    overlap = token_f1(response, ground_truth)
    score += 0.4 * overlap

    return max(1.0, min(7.0, score))


def similarity_score(response: str, ground_truth: str) -> float:
    """Dummy Sim-RL reward in [0, 1]."""
    return token_f1(response, ground_truth)
