"""Write per-model labels, metrics JSON, histograms, and RESULTS files.

Run from the experiment folder:

    uv run python scripts/run_jev.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from shared.data import (
    SAMPLE_GOLD_0_COUNT,
    SAMPLE_GOLD_1_COUNT,
    SAMPLE_ROW_COUNT,
)
from shared.engine_loop import DEADLETTER_FILENAME, LABELS_FILENAME, LabelTask
from shared.metrics import classification_report, latency_percentiles
from shared.records import PredictionRecord

RESULT_KEYS = (
    "model_name",
    "n_scored",
    "n_deadletter",
    "f1",
    "accuracy",
    "precision",
    "recall",
    "p50",
    "p90",
    "p99",
    "total_input_tokens",
    "total_output_tokens",
    "estimated_cost_usd",
)


def require_sample_manifest(manifest_path: Path) -> dict[str, object]:
    """Exit if the on-disk sample is not 1000/560/440."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    counts_match = (
        manifest.get("n_rows") == SAMPLE_ROW_COUNT
        and manifest.get("n_gold_0") == SAMPLE_GOLD_0_COUNT
        and manifest.get("n_gold_1") == SAMPLE_GOLD_1_COUNT
    )
    if not counts_match:
        raise SystemExit(
            f"Sample manifest is not {SAMPLE_ROW_COUNT}/{SAMPLE_GOLD_0_COUNT}/"
            f"{SAMPLE_GOLD_1_COUNT}: {manifest_path}"
        )
    return manifest


def assert_run_complete(n_scored: int, n_deadletter: int, expected_n: int) -> None:
    """Exit without writing a finished results.json for a partial run."""
    if n_scored + n_deadletter != expected_n:
        raise SystemExit(
            f"Incomplete run: scored={n_scored} deadletter={n_deadletter} "
            f"expected={expected_n}; not writing results.json"
        )


def tasks_from_sample(frame: pd.DataFrame) -> list[LabelTask]:
    """Build label tasks from the sample table."""
    return [
        LabelTask(
            source_row_id=str(row.source_row_id),
            text=str(row.text),
            gold_label=int(row.gold_label),
        )
        for row in frame.itertuples(index=False)
    ]


def write_model_outputs(
    records: list[PredictionRecord],
    deadletters: list[dict[str, object]],
    output_dir: Path,
) -> dict[str, object]:
    """Write results.json, RESULTS.md, and a probability histogram.

    Parameters
    ----------
    records
        Successfully scored rows.
    deadletters
        Failed rows already written or collected.
    output_dir
        Model output directory.

    Returns
    -------
    dict[str, object]
        The results.json payload.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = _results_payload(records, deadletters)
    (output_dir / "results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    hist_path = write_score_histogram(records, output_dir / "static")
    (output_dir / "RESULTS.md").write_text(
        _model_results_markdown(payload, hist_path), encoding="utf-8"
    )
    return payload


def write_score_histogram(
    records: list[PredictionRecord], static_dir: Path
) -> Path | None:
    """Write a bar histogram of probabilities, or skip if all are missing."""
    values = [record.probability for record in records if record.probability is not None]
    if not values:
        return None
    static_dir.mkdir(parents=True, exist_ok=True)
    hist_path = static_dir / "score_hist.png"
    figure, axis = plt.subplots()
    axis.hist(values, bins=10, range=(0.0, 1.0))
    axis.set_xlabel("probability")
    axis.set_ylabel("count")
    figure.savefig(hist_path)
    plt.close(figure)
    return hist_path


def load_records_from_output(output_dir: Path) -> list[PredictionRecord]:
    """Load PredictionRecords from labels.parquet if present."""
    labels_path = output_dir / LABELS_FILENAME
    if not labels_path.is_file():
        return []
    frame = pd.read_parquet(labels_path)
    return [PredictionRecord.model_validate(row) for row in frame.to_dict(orient="records")]


def load_deadletters(output_dir: Path) -> list[dict[str, object]]:
    """Load deadletter JSON lines, or an empty list."""
    path = output_dir / DEADLETTER_FILENAME
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line]


def _results_payload(
    records: list[PredictionRecord], deadletters: list[dict[str, object]]
) -> dict[str, object]:
    gold = [record.gold_label for record in records]
    pred = [record.binary_label for record in records]
    report = (
        classification_report(gold, pred)
        if records
        else {"f1": 0.0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0}
    )
    latencies = [record.latency_ms for record in records]
    percentiles = (
        latency_percentiles(latencies)
        if latencies
        else {"p50": 0.0, "p90": 0.0, "p99": 0.0}
    )
    model_name = records[0].model_name if records else "unknown"
    return {
        "model_name": model_name,
        "n_scored": len(records),
        "n_deadletter": len(deadletters),
        **report,
        **percentiles,
        "total_input_tokens": sum(
            record.input_tokens or 0 for record in records
        ),
        "total_output_tokens": sum(
            record.output_tokens or 0 for record in records
        ),
        "estimated_cost_usd": sum(record.estimated_cost_usd for record in records),
    }


def _model_results_markdown(payload: dict[str, object], hist_path: Path | None) -> str:
    hist_line = (
        f"Histogram: `{hist_path}`"
        if hist_path is not None
        else "Histogram skipped because every probability was null."
    )
    deadletter_line = f"Deadletter rows: {payload['n_deadletter']}"
    if payload["n_deadletter"] == 0:
        deadletter_line = "No failures."
    return (
        f"# {payload['model_name']}\n\n"
        f"| metric | value |\n| --- | ---: |\n"
        f"| n_scored | {payload['n_scored']} |\n"
        f"| n_deadletter | {payload['n_deadletter']} |\n"
        f"| f1 | {payload['f1']} |\n"
        f"| accuracy | {payload['accuracy']} |\n"
        f"| precision | {payload['precision']} |\n"
        f"| recall | {payload['recall']} |\n"
        f"| p50 | {payload['p50']} |\n"
        f"| p90 | {payload['p90']} |\n"
        f"| p99 | {payload['p99']} |\n"
        f"| total_input_tokens | {payload['total_input_tokens']} |\n"
        f"| total_output_tokens | {payload['total_output_tokens']} |\n"
        f"| estimated_cost_usd | {payload['estimated_cost_usd']} |\n\n"
        f"{hist_line}\n\n"
        f"{deadletter_line}\n"
    )
