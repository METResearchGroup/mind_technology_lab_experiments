"""Fixture tests for sample-job outputs. No live providers."""

import json
from pathlib import Path

import pandas as pd
import pytest

from shared.data import SAMPLE_GOLD_0_COUNT, SAMPLE_GOLD_1_COUNT, SAMPLE_ROW_COUNT
from shared.engine_loop import LabelTask, label_records
from shared.metrics import binary_label_from_probability
from shared.records import MODEL_NAME_JEV, PredictionRecord
from shared.run_outputs import (
    RESULT_KEYS,
    assert_run_complete,
    outstanding_deadletters,
    require_sample_manifest,
    tasks_from_sample,
    write_model_outputs,
    write_score_histogram,
)


def _record(task: LabelTask) -> PredictionRecord:
    probability = 0.8 if task.gold_label == 1 else 0.2
    return PredictionRecord(
        source_row_id=task.source_row_id,
        text=task.text,
        gold_label=task.gold_label,
        model_name=MODEL_NAME_JEV,
        probability=probability,
        binary_label=binary_label_from_probability(probability),
        latency_ms=4.0,
        input_tokens=2,
        output_tokens=1,
        estimated_cost_usd=0.0,
    )


def _four_row_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "source_row_id": ["a", "b", "c", "d"],
            "text": ["t1", "t2", "t3", "t4"],
            "gold_label": [0, 0, 1, 1],
            "tweet_id": [None, None, None, None],
        }
    )


class TestWriteModelOutputs:
    """Tests for write_model_outputs()."""

    def test_results_json_counts_match_four_rows(self, tmp_path: Path) -> None:
        """n_scored plus n_deadletter equals the four-row fixture."""
        tasks = tasks_from_sample(_four_row_sample())
        records = [_record(task) for task in tasks[:3]]
        deadletters = [
            {"source_row_id": "d", "error": "x", "attempts": 4, "batch_index": 0}
        ]

        payload = write_model_outputs(records, deadletters, tmp_path)

        assert set(payload) >= set(RESULT_KEYS)
        assert payload["n_scored"] + payload["n_deadletter"] == 4
        saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
        assert saved["n_scored"] == 3
        assert saved["n_deadletter"] == 1


class TestSkipSeenOnRerun:
    """Tests that an existing parquet skips already scored ids."""

    def test_label_one_called_twice_when_two_ids_exist(self, tmp_path: Path) -> None:
        """Two existing labels leave two unseen tasks."""
        tasks = tasks_from_sample(_four_row_sample())
        existing = pd.DataFrame([_record(task).model_dump() for task in tasks[:2]])
        existing.to_parquet(tmp_path / "labels.parquet", index=False)
        called: list[str] = []

        def label_one(task: LabelTask) -> PredictionRecord:
            called.append(task.source_row_id)
            return _record(task)

        label_records(tasks, label_one, tmp_path, batch_size=8, max_label_retries=3)

        assert called == ["c", "d"]


class TestRequireSampleManifest:
    """Tests for require_sample_manifest()."""

    def test_wrong_n_rows_exits_before_scoring(self, tmp_path: Path) -> None:
        """A manifest that is not 1000 rows exits non-zero."""
        manifest_path = tmp_path / "sample_1000.manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "source_uri": "s3://example/x.csv",
                    "seed": 1,
                    "n_rows": 4,
                    "n_gold_0": 2,
                    "n_gold_1": 2,
                    "row_id_field": "source_row_id",
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(SystemExit):
            require_sample_manifest(manifest_path)

        assert SAMPLE_ROW_COUNT == 1000
        assert SAMPLE_GOLD_0_COUNT == 560
        assert SAMPLE_GOLD_1_COUNT == 440


class TestAssertRunComplete:
    """Tests for assert_run_complete()."""

    def test_partial_counts_exit(self) -> None:
        """A partial scored-plus-deadletter count exits before results.json."""
        with pytest.raises(SystemExit):
            assert_run_complete(n_scored=2, n_deadletter=0, expected_n=4)

    def test_complete_counts_pass(self) -> None:
        """Matching counts do not exit."""
        assert_run_complete(n_scored=3, n_deadletter=1, expected_n=4)


class TestWriteScoreHistogram:
    """Tests for write_score_histogram()."""

    def test_skips_file_when_all_probabilities_null(self, tmp_path: Path) -> None:
        """No histogram file when every probability is missing."""
        task = tasks_from_sample(_four_row_sample())[0]
        record = PredictionRecord(
            source_row_id=task.source_row_id,
            text=task.text,
            gold_label=task.gold_label,
            model_name=MODEL_NAME_JEV,
            probability=None,
            binary_label=0,
            latency_ms=1.0,
            input_tokens=None,
            output_tokens=None,
            estimated_cost_usd=0.0,
        )

        result = write_score_histogram([record], tmp_path / "static")

        assert result is None
        assert not (tmp_path / "static" / "score_hist.png").exists()


class TestOutstandingDeadletters:
    """Tests for outstanding_deadletters()."""

    def test_drops_ids_that_later_scored(self) -> None:
        """A later successful label removes that id from the deadletter count."""
        tasks = tasks_from_sample(_four_row_sample())
        records = [_record(task) for task in tasks[:3]]
        deadletters = [
            {"source_row_id": "c", "error": "old", "attempts": 4, "batch_index": 0},
            {"source_row_id": "d", "error": "x", "attempts": 4, "batch_index": 0},
        ]

        result = outstanding_deadletters(records, deadletters)

        assert [row["source_row_id"] for row in result] == ["d"]
