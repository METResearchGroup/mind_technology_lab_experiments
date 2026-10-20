"""Cascade stack policy: high P blocks, low P allows, else guardrail."""

from __future__ import annotations

from collections.abc import Callable

from scorers.guardrails import GuardrailStrength, band_blocks_at_strength
from shared.records import PredictionRecord


def cascade_decisions(
    predictions: list[PredictionRecord],
    *,
    threshold_high: float,
    threshold_low: float,
    guardrail_strength: GuardrailStrength,
    harm_probability: Callable[[PredictionRecord], float | None],
    guardrail_band_for: Callable[[str], str | None],
) -> list[bool]:
    """Return per-row block decisions for the cascade policy."""
    out: list[bool] = []
    for pred in predictions:
        prob = harm_probability(pred)
        if prob is not None and prob >= threshold_high:
            out.append(True)
            continue
        if prob is not None and prob <= threshold_low:
            out.append(False)
            continue
        band = guardrail_band_for(pred.example_id)
        guard_block = (
            band is not None
            and band_blocks_at_strength(band, guardrail_strength)
        )
        out.append(guard_block)
    return out
