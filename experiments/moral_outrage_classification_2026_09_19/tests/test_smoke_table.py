"""Tests for the smoke cost table builder."""

import ast
from pathlib import Path

from models.smoke_tests.table import build_smoke_table
from shared.metrics import binary_label_from_probability
from shared.records import (
    BEDROCK_MODEL_NAMES,
    MODEL_NAME_JEV,
    MODEL_NAME_PERSPECTIVE,
    PredictionRecord,
)


def _record(model_name: str, probability: float, latency_ms: float) -> PredictionRecord:
    return PredictionRecord(
        source_row_id="0",
        text="x",
        gold_label=0,
        model_name=model_name,
        probability=probability,
        binary_label=binary_label_from_probability(probability),
        latency_ms=latency_ms,
        input_tokens=10,
        output_tokens=2,
        estimated_cost_usd=0.0,
    )


class TestBuildSmokeTable:
    """Tests for build_smoke_table()."""

    def test_row_order_and_columns(self) -> None:
        """Seven models appear in the locked order with required columns."""
        records = []
        names = (MODEL_NAME_JEV, MODEL_NAME_PERSPECTIVE, *BEDROCK_MODEL_NAMES)
        for name in names:
            records.extend(
                [
                    _record(name, 0.9, 10.0),
                    _record(name, 0.1, 20.0),
                    _record(name, 0.4, 30.0),
                ]
            )

        result = build_smoke_table(records)

        assert [row["model_name"] for row in result] == list(names)
        assert set(result[0]) == {
            "model_name",
            "total_tokens",
            "estimated_cost",
            "estimated_runtime_ms",
        }
        assert result[0]["total_tokens"] == 36
        assert result[0]["estimated_runtime_ms"] == 20.0

    def test_perspective_cost_is_zero(self) -> None:
        """Perspective estimated cost is 0.000000."""
        records = [_record(MODEL_NAME_PERSPECTIVE, 0.2, 5.0) for _ in range(3)]
        # Need all seven models present for order; fill others with one record each.
        records.extend(_record(MODEL_NAME_JEV, 0.2, 5.0) for _ in range(3))
        for name in BEDROCK_MODEL_NAMES:
            records.extend(_record(name, 0.2, 5.0) for _ in range(3))

        result = build_smoke_table(records)
        perspective = next(
            row for row in result if row["model_name"] == MODEL_NAME_PERSPECTIVE
        )
        assert perspective["estimated_cost"] == "0.000000"


class TestSmokeMainDoesNotReadSample:
    """Tests that smoke entrypoints stay off the sample file."""

    def test_main_source_does_not_touch_sample(self) -> None:
        """The smoke package main does not import sample writers or parquet."""
        main_path = (
            Path(__file__).resolve().parents[1]
            / "models"
            / "smoke_tests"
            / "__main__.py"
        )
        source = main_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert "shared.data" not in imported
        assert "write_sample_if_missing" not in source
        assert "sample_1000.parquet" not in source
