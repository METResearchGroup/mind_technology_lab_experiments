"""Lexical proxies for the paper's 1-5 user-likeness dimensions."""

from __future__ import annotations

import re
from typing import TypedDict

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


class StyleScores(TypedDict):
    brevity: float
    informality: float
    information_pacing: float
    mean: float
    word_count: int


def _clip_score(value: float) -> float:
    return float(min(5.0, max(1.0, value)))


def score_user_likeness(message: str) -> StyleScores:
    """Score a request with cheap lexical rules that track the paper's axes.

    This is not the GPT-5 Mini judge. It is a stand-in for the dashboard and
    for tests of the steering pipeline.
    """
    text = message.strip()
    words = re.findall(r"[A-Za-z0-9']+", text)
    n_words = max(len(words), 1)
    brevity = _clip_score(6.2 - 0.09 * n_words)
    contraction_hits = len(_CONTRACTIONS.findall(text))
    formal_hits = len(_FORMAL.findall(text))
    starts_lower = 1.0 if text[:1].islower() else 0.0
    has_question_only = 1.0 if text.endswith("?") and n_words <= 12 else 0.0
    informality = _clip_score(
        2.2 + 0.7 * contraction_hits + 0.6 * starts_lower + 0.5 * has_question_only
        - 0.45 * formal_hits
    )
    detail_hits = len(_DETAIL.findall(text))
    comma_count = text.count(",")
    pacing = _clip_score(4.8 - 0.35 * detail_hits - 0.15 * comma_count - 0.03 * n_words)
    mean = (brevity + informality + pacing) / 3.0
    return {
        "brevity": brevity,
        "informality": informality,
        "information_pacing": pacing,
        "mean": mean,
        "word_count": len(words),
    }
