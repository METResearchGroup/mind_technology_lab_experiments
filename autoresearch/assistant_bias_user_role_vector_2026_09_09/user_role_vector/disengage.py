"""Disengagement prediction metrics from section 3.2."""

from __future__ import annotations

from collections.abc import Sequence

CONTINUE = "continue"
DISENGAGE = "disengage"


def first_disengage_turn(
    predictions: Sequence[str],
    *,
    final_turn: int | None = None,
) -> int:
    """Return the first predicted disengage turn, or the final continue turn."""
    if not predictions:
        raise ValueError("predictions must not be empty")
    n_turns = len(predictions)
    last = final_turn if final_turn is not None else n_turns
    for index, label in enumerate(predictions, start=1):
        if label not in {CONTINUE, DISENGAGE}:
            raise ValueError(f"unknown prediction: {label!r}")
        if label == DISENGAGE:
            return index
    return last


def disengagement_distance(predicted_turn: int, true_turn: int) -> int:
    return abs(predicted_turn - true_turn)


def exact_match_rate(
    predicted_turns: Sequence[int],
    true_turns: Sequence[int],
) -> float:
    if len(predicted_turns) != len(true_turns):
        raise ValueError("predicted and true turns must have the same length")
    if not predicted_turns:
        raise ValueError("need at least one dialogue")
    matches = sum(
        predicted == true
        for predicted, true in zip(predicted_turns, true_turns, strict=True)
    )
    return matches / len(predicted_turns)


def disengagement_rate(
    predicted_turns: Sequence[int],
    *,
    final_turn: int,
) -> float:
    """Share of dialogues that disengage before the last turn."""
    if not predicted_turns:
        raise ValueError("need at least one dialogue")
    early = sum(turn < final_turn for turn in predicted_turns)
    return early / len(predicted_turns)
