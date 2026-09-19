"""Tests for PredictionRecord validation and thresholding."""

import pytest
from pydantic import ValidationError

from shared.records import (
    MODEL_NAME_JEV,
    POSITIVE_PROBABILITY_THRESHOLD,
    PredictionRecord,
)


def _record(probability: float | None, binary_label: int) -> PredictionRecord:
    return PredictionRecord(
        source_row_id="0",
        text="example",
        gold_label=1,
        model_name=MODEL_NAME_JEV,
        probability=probability,
        binary_label=binary_label,
        latency_ms=1.0,
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=0.0,
    )


class TestPredictionRecord:
    """Tests for PredictionRecord."""

    def test_rejects_probability_above_one(self) -> None:
        """Probability outside [0, 1] is invalid when present."""
        with pytest.raises(ValidationError):
            _record(1.2, 1)

    def test_rejects_probability_below_zero(self) -> None:
        """Negative probability is invalid."""
        with pytest.raises(ValidationError):
            _record(-0.1, 0)

    def test_threshold_constant_is_one_half(self) -> None:
        """Binary conversion uses 0.5."""
        assert POSITIVE_PROBABILITY_THRESHOLD == 0.5
