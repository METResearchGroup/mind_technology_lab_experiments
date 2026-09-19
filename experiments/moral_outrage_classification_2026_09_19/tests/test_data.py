"""Tests for sample drawing and full-frame validation."""

import pandas as pd
import pytest

from shared.data import (
    SAMPLE_SEED,
    draw_stratified_sample,
    validate_full_frame,
)


def _ten_row_fixture() -> pd.DataFrame:
    gold_labels = [0, 0, 0, 0, 0, 0, 1, 1, 1, 1]
    return pd.DataFrame(
        {
            "source_row_id": [str(i) for i in range(10)],
            "text": [f"post {i}" for i in range(10)],
            "gold_label": gold_labels,
            "tweet_id": [None] * 10,
        }
    )


class TestDrawStratifiedSample:
    """Tests for draw_stratified_sample()."""

    def test_explicit_counts_preserve_class_mix(self) -> None:
        """A 6/4 fixture sampled 3/2 keeps those class counts."""
        frame = _ten_row_fixture()
        n_gold_0 = 3
        n_gold_1 = 2

        result = draw_stratified_sample(frame, n_gold_0, n_gold_1, SAMPLE_SEED)

        assert int((result.gold_label == 0).sum()) == n_gold_0
        assert int((result.gold_label == 1).sum()) == n_gold_1
        assert len(result) == n_gold_0 + n_gold_1

    def test_same_seed_returns_same_row_ids(self) -> None:
        """Two draws with the same seed and input share source_row_id order."""
        frame = _ten_row_fixture()
        n_gold_0 = 3
        n_gold_1 = 2

        first = draw_stratified_sample(frame, n_gold_0, n_gold_1, SAMPLE_SEED)
        second = draw_stratified_sample(frame, n_gold_0, n_gold_1, SAMPLE_SEED)

        assert list(first.source_row_id) == list(second.source_row_id)


class TestValidateFullFrame:
    """Tests for validate_full_frame()."""

    def test_wrong_gold_counts_raise(self) -> None:
        """A fixture that is not 14563/11437 fails validation."""
        frame = _ten_row_fixture()

        with pytest.raises((ValueError, SystemExit)):
            validate_full_frame(frame)
