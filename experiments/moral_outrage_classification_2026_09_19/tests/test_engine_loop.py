"""Tests for skip-seen and deadletter behavior in the shared engine loop."""

import json
from pathlib import Path

import pandas as pd
import pytest

from shared.engine_loop import LabelTask, label_records
from shared.metrics import binary_label_from_probability
from shared.records import MODEL_NAME_JEV, PredictionRecord


def _task(source_row_id: str) -> LabelTask:
    return LabelTask(source_row_id=source_row_id, text=f"text {source_row_id}", gold_label=0)


def _record(source_row_id: str) -> PredictionRecord:
    probability = 0.9
    return PredictionRecord(
        source_row_id=source_row_id,
        text=f"text {source_row_id}",
        gold_label=0,
        model_name=MODEL_NAME_JEV,
        probability=probability,
        binary_label=binary_label_from_probability(probability),
        latency_ms=1.0,
        input_tokens=1,
        output_tokens=1,
        estimated_cost_usd=0.0,
    )


class TestLabelRecords:
    """Tests for label_records()."""

    def test_skips_source_row_ids_already_in_parquet(self, tmp_path: Path) -> None:
        """An existing first-row label means only the second task is scored."""
        existing = pd.DataFrame([_record("1").model_dump()])
        existing.to_parquet(tmp_path / "labels.parquet", index=False)
        called: list[str] = []

        def label_one(task: LabelTask) -> PredictionRecord:
            called.append(task.source_row_id)
            return _record(task.source_row_id)

        label_records(
            [_task("1"), _task("2")],
            label_one,
            tmp_path,
            batch_size=8,
            max_label_retries=3,
        )

        assert called == ["2"]

    def test_deadletter_after_four_attempts(self, tmp_path: Path) -> None:
        """TimeoutError on every attempt writes deadletter attempts==4."""

        def label_one(_task: LabelTask) -> PredictionRecord:
            raise TimeoutError("slow")

        label_records(
            [_task("9")],
            label_one,
            tmp_path,
            batch_size=1,
            max_label_retries=3,
        )

        deadletter_path = tmp_path / "deadletter.jsonl"
        lines = deadletter_path.read_text(encoding="utf-8").strip().splitlines()
        payload = json.loads(lines[0])
        assert payload["source_row_id"] == "9"
        assert payload["attempts"] == 4
        assert "error" in payload
        labels_path = tmp_path / "labels.parquet"
        if labels_path.is_file():
            assert len(pd.read_parquet(labels_path)) == 0
