"""Fixture tests for root RESULTS and S3 key mapping."""

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.upload_s3 import PREFIX, s3_key_for_local_path, upload_tree
from scripts.write_root_results import pair_probabilities, write_root_results
from shared.metrics import binary_label_from_probability
from shared.records import MODEL_NAME_JEV, MODEL_NAME_PERSPECTIVE, PredictionRecord


def _payload(model_name: str) -> dict[str, object]:
    return {
        "model_name": model_name,
        "n_scored": 4,
        "n_deadletter": 0,
        "f1": 0.5,
        "accuracy": 0.5,
        "precision": 0.5,
        "recall": 0.5,
        "p50": 10.0,
        "p90": 12.0,
        "p99": 13.0,
        "total_input_tokens": 20,
        "total_output_tokens": 4,
        "estimated_cost_usd": 0.0,
    }


def _write_model(
    directory: Path, model_name: str, row_ids: list[str], probabilities: list[float]
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for row_id, probability in zip(row_ids, probabilities, strict=True):
        records.append(
            PredictionRecord(
                source_row_id=row_id,
                text="t",
                gold_label=1,
                model_name=model_name,
                probability=probability,
                binary_label=binary_label_from_probability(probability),
                latency_ms=1.0,
                input_tokens=1,
                output_tokens=1,
                estimated_cost_usd=0.0,
            ).model_dump()
        )
    pd.DataFrame(records).to_parquet(directory / "labels.parquet", index=False)
    (directory / "results.json").write_text(
        json.dumps(_payload(model_name), indent=2), encoding="utf-8"
    )


class TestWriteRootResults:
    """Tests for write_root_results()."""

    def test_writes_tables_and_difference_stats(self, tmp_path: Path) -> None:
        """RESULTS.md contains the three tables and four difference numbers."""
        outputs = tmp_path / "outputs"
        _write_model(
            outputs / "jev",
            MODEL_NAME_JEV,
            ["1", "2", "3"],
            [0.8, 0.2, 0.6],
        )
        _write_model(
            outputs / "perspective_api",
            MODEL_NAME_PERSPECTIVE,
            ["1", "2", "3"],
            [0.5, 0.4, 0.1],
        )
        for model_id in (
            "us.openai.gpt-5.6-luna",
            "us.openai.gpt-5.6-terra",
            "us.anthropic.claude-sonnet-5",
            "qwen.qwen3-32b-v1:0",
            "deepseek.v3-v1:0",
        ):
            _write_model(
                outputs / "bedrock" / model_id,
                f"Bedrock:{model_id}",
                ["1"],
                [0.9],
            )
        results_path = tmp_path / "RESULTS.md"
        comparison = outputs / "comparison"

        summary = write_root_results(outputs, results_path, comparison)
        text = results_path.read_text(encoding="utf-8")

        assert "## Quality" in text
        assert "## Latency" in text
        assert "## Cost" in text
        assert "mean" in text
        for key in ("mean", "median", "std", "iqr"):
            assert key in summary
        saved = json.loads(
            (comparison / "difference_summary.json").read_text(encoding="utf-8")
        )
        assert saved["n_paired"] == 3

    def test_missing_results_exits(self, tmp_path: Path) -> None:
        """A missing per-model results.json exits before rewriting RESULTS.md."""
        results_path = tmp_path / "RESULTS.md"
        results_path.write_text("keep", encoding="utf-8")

        with pytest.raises(SystemExit):
            write_root_results(tmp_path / "outputs", results_path, tmp_path / "cmp")

        assert results_path.read_text(encoding="utf-8") == "keep"


class TestPairProbabilities:
    """Tests for pair_probabilities()."""

    def test_shared_ids_length_three(self) -> None:
        """Three shared source_row_ids produce three differences."""
        jev = pd.DataFrame(
            {"source_row_id": ["1", "2", "3"], "probability": [0.8, 0.2, 0.6]}
        )
        perspective = pd.DataFrame(
            {"source_row_id": ["1", "2", "3"], "probability": [0.5, 0.4, 0.1]}
        )

        paired, n_dropped = pair_probabilities(jev, perspective)

        assert len(paired) == 3
        assert n_dropped == 0

    def test_counts_id_only_in_jev(self) -> None:
        """An id present only in Jev is counted in n_dropped."""
        jev = pd.DataFrame(
            {"source_row_id": ["1", "2"], "probability": [0.8, 0.2]}
        )
        perspective = pd.DataFrame(
            {"source_row_id": ["1"], "probability": [0.5]}
        )

        paired, n_dropped = pair_probabilities(jev, perspective)

        assert len(paired) == 1
        assert n_dropped == 1

    def test_counts_id_missing_probability_on_both(self) -> None:
        """An id present on both sides with no probability is dropped."""
        jev = pd.DataFrame(
            {"source_row_id": ["1"], "probability": [None]}
        )
        perspective = pd.DataFrame(
            {"source_row_id": ["1"], "probability": [None]}
        )

        paired, n_dropped = pair_probabilities(jev, perspective)

        assert len(paired) == 0
        assert n_dropped == 1


class TestS3KeyMapping:
    """Tests for s3_key_for_local_path()."""

    def test_maps_outputs_jev_results(self, tmp_path: Path) -> None:
        """Local outputs/jev/results.json maps to the experiment prefix."""
        experiment_root = tmp_path / "experiments" / "moral_outrage_classification_2026_09_19"
        local = experiment_root / "outputs" / "jev" / "results.json"
        local.parent.mkdir(parents=True)
        local.write_text("{}", encoding="utf-8")

        result = s3_key_for_local_path(local, experiment_root)

        assert result == PREFIX + "outputs/jev/results.json"

    def test_upload_tree_uses_prefix_and_skips_full_csv(self, tmp_path: Path) -> None:
        """A fake put_object receives the experiment prefix and skips the 26k CSV."""
        experiment_root = tmp_path / "experiments" / "moral_outrage_classification_2026_09_19"
        uploaded = experiment_root / "outputs" / "jev" / "results.json"
        uploaded.parent.mkdir(parents=True)
        uploaded.write_text("{}", encoding="utf-8")
        csv_path = experiment_root / "data" / "26k_training_data.csv"
        csv_path.parent.mkdir(parents=True)
        csv_path.write_text("text,outrage\n", encoding="utf-8")
        venv_file = experiment_root / ".venv" / "lib" / "pkg.py"
        venv_file.parent.mkdir(parents=True)
        venv_file.write_text("x", encoding="utf-8")
        env_path = experiment_root / ".env"
        env_path.write_text("SECRET=1", encoding="utf-8")
        cache_file = experiment_root / ".pytest_cache" / "v" / "cache"
        cache_file.parent.mkdir(parents=True)
        cache_file.write_text("x", encoding="utf-8")
        keys: list[str] = []

        def put_object(*, Bucket: str, Key: str, Body: bytes) -> None:
            keys.append(Key)

        result = upload_tree(experiment_root, put_object)

        assert PREFIX + "outputs/jev/results.json" in result
        assert PREFIX + "data/26k_training_data.csv" not in keys
        assert PREFIX + ".env" not in keys
        assert not any(".venv" in key for key in keys)
        assert not any(".pytest_cache" in key for key in keys)
