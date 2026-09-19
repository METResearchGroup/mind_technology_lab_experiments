"""Tests for thresholding, classification metrics, and latency percentiles."""

import math

import pytest

from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS
from shared.metrics import (
    binary_label_from_probability,
    classification_report,
    latency_percentiles,
    paired_difference_summary,
)


class TestBinaryLabelFromProbability:
    """Tests for binary_label_from_probability()."""

    @pytest.mark.parametrize(
        ("probability", "expected"),
        [(0.5, 1), (0.499, 0), (1.0, 1), (0.0, 0)],
    )
    def test_threshold_at_one_half(self, probability: float, expected: int) -> None:
        """0.5 and above are positive."""
        result = binary_label_from_probability(probability)
        assert result == expected


class TestClassificationReport:
    """Tests for classification_report()."""

    def test_mixed_predictions(self) -> None:
        """Gold [1,1,0,0] and pred [1,0,0,0] match the locked metric values."""
        gold = [1, 1, 0, 0]
        pred = [1, 0, 0, 0]
        expected_f1 = 2.0 / 3.0

        result = classification_report(gold, pred)

        assert result["accuracy"] == 0.75
        assert result["precision"] == 1.0
        assert result["recall"] == 0.5
        assert result["f1"] == expected_f1

    def test_all_negative_zero_division(self) -> None:
        """No predicted or gold positives yields precision, recall, and F1 of 0."""
        gold = [0, 0]
        pred = [0, 0]

        result = classification_report(gold, pred)

        assert result["precision"] == 0.0
        assert result["recall"] == 0.0
        assert result["f1"] == 0.0
        assert result["accuracy"] == 1.0


class TestLatencyPercentiles:
    """Tests for latency_percentiles()."""

    def test_ordered_sample_percentiles(self) -> None:
        """p50 is the linear median; p90 and p99 are at least p50."""
        latency_ms = [10.0, 20.0, 30.0, 40.0, 50.0]

        result = latency_percentiles(latency_ms)

        assert result["p50"] == 30.0
        assert result["p90"] >= result["p50"]
        assert result["p99"] >= result["p50"]


class TestPairedDifferenceSummary:
    """Tests for paired_difference_summary()."""

    def test_two_pair_summary(self) -> None:
        """Differences [0.3, -0.2] have mean and median 0.05."""
        jev = [0.8, 0.2]
        perspective = [0.5, 0.4]
        expected_std = math.sqrt(0.125)

        result = paired_difference_summary(jev, perspective)

        assert result["mean"] == pytest.approx(0.05)
        assert result["median"] == pytest.approx(0.05)
        assert result["std"] == pytest.approx(expected_std)
        assert result["iqr"] == pytest.approx(0.25)


class TestBradyDefinition:
    """Tests for BRADY_MORAL_OUTRAGE_INSTRUCTIONS."""

    def test_contains_three_parts(self) -> None:
        """The shared string includes the three Brady parts."""
        text = BRADY_MORAL_OUTRAGE_INSTRUCTIONS
        assert "perceived moral violation" in text
        assert "anger or disgust or contempt" in text
        assert "blame or a wish to punish" in text
