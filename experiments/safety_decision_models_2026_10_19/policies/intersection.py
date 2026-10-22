"""Intersection stack policy: block if guardrail blocks and P(harm) >= threshold."""

from __future__ import annotations

from collections.abc import Callable

from scorers.guardrails import GuardrailStrength, band_blocks_at_strength
from shared.records import PredictionRecord


def intersection_decisions(
    predictions: list[PredictionRecord],
    *,
    threshold: float,
    guardrail_strength: GuardrailStrength,
    harm_probability: Callable[[PredictionRecord], float | None],
    guardrail_band_for: Callable[[str], str | None],
) -> list[bool]:
    """Return per-row block decisions for the intersection policy."""
    out: list[bool] = []
    for pred in predictions:
        prob = harm_probability(pred)
        model_block = prob is not None and prob >= threshold
        band = guardrail_band_for(pred.example_id)
        guard_block = (
            band is not None
            and band_blocks_at_strength(band, guardrail_strength)
        )
        out.append(model_block and guard_block)
    return out
