"""Run one full Jev pass for a batch size and write pass outputs.

Run from the experiment folder:

    uv run python scripts/run_batch_size.py --batch-size 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from pydantic import BaseModel  # noqa: E402

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from models.batched_jev import build_live_scorer  # noqa: E402
from shared.batch_runner import (  # noqa: E402
    DEADLETTER_FILENAME,
    PREDICTIONS_FILENAME,
    REQUESTS_FILENAME,
    RUNS_FILENAME,
    run_pass,
)
from shared.data import load_sample  # noqa: E402
from shared.metrics import (  # noqa: E402
    summarize_pass_predictions,
    summarize_pass_requests,
)
from shared.pricing import PRICE_PAGE_DATE, PRICE_PAGE_URL  # noqa: E402
from shared.rate_limiter import (  # noqa: E402
    MAX_REQUEST_STARTS_PER_MINUTE,
    RequestStartLimiter,
)
from shared.records import PostPrediction, PostTask, RequestLog  # noqa: E402
from shared.secrets import load_typesafe_api_key  # noqa: E402

ALLOWED_BATCH_SIZES: tuple[int, ...] = (1, 5, 10, 20, 30, 40)
HISTOGRAM_BINS = 10
HISTOGRAM_RANGE = (0.0, 1.0)
OUTPUTS_ROOT = EXPERIMENT_ROOT / "outputs"
ROW_ID_COLUMN = "source_row_id"
TEXT_COLUMN = "text"
GOLD_LABEL_COLUMN = "gold_label"
LABELS_FILENAME = "labels.parquet"
REQUESTS_PARQUET_FILENAME = "requests.parquet"
RESULTS_FILENAME = "results.json"
RESULTS_MARKDOWN_FILENAME = "RESULTS.md"
STATIC_DIRNAME = "static"
HISTOGRAM_FILENAME = "score_hist.png"
PRICE_SOURCE = f"{PRICE_PAGE_URL} ({PRICE_PAGE_DATE})"


class RequestLatencyMs(BaseModel):
    """Request latency percentiles in milliseconds."""

    p50: float
    p90: float
    p99: float


class PassResults(BaseModel):
    """Serialized pass metrics written to ``results.json``."""

    batch_size: int
    n_scored: int
    n_deadletter: int
    n_requests: int
    f1: float
    accuracy: float
    precision: float
    recall: float
    request_latency_ms: RequestLatencyMs
    per_post_latency_ms_p50: float
    wall_time_seconds: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    model_versions: list[str]
    price_source: str


def main() -> None:
    """Parse args, run one pass, and write parquet, metrics, and RESULTS."""
    batch_size = _parse_batch_size()
    tasks = _load_tasks()
    output_dir = _output_dir(batch_size)
    scorer = build_live_scorer(load_typesafe_api_key())
    limiter = RequestStartLimiter(MAX_REQUEST_STARTS_PER_MINUTE)
    run_pass(tasks, batch_size, output_dir, scorer, limiter)
    predictions = _load_deduped_predictions(output_dir / PREDICTIONS_FILENAME)
    requests = _load_requests(output_dir / REQUESTS_FILENAME)
    _write_parquet_outputs(predictions, requests, output_dir)
    results = _build_pass_results(batch_size, predictions, requests, output_dir)
    _write_results_json(output_dir, results)
    _write_score_histogram(predictions, output_dir / STATIC_DIRNAME)
    _write_results_markdown(output_dir, results)


def _parse_batch_size() -> int:
    """Parse and validate the required ``--batch-size`` CLI argument."""
    parser = argparse.ArgumentParser(description="Run one Jev batch-size pass.")
    parser.add_argument(
        "--batch-size",
        type=int,
        choices=ALLOWED_BATCH_SIZES,
        required=True,
        help=f"Posts per request; allowed values: {ALLOWED_BATCH_SIZES}",
    )
    return parser.parse_args().batch_size


def _load_tasks() -> list[PostTask]:
    """Load the full sample as scoring tasks."""
    sample = load_sample()
    return _frame_to_tasks(sample)


def _output_dir(batch_size: int) -> Path:
    """Return the output directory for one batch-size pass."""
    return OUTPUTS_ROOT / f"batch_{batch_size}"


def _load_deduped_predictions(predictions_path: Path) -> list[PostPrediction]:
    """Load predictions JSONL and keep the latest row per ``source_row_id``."""
    predictions = _read_predictions_jsonl(predictions_path)
    return _dedupe_predictions(predictions)


def _load_requests(requests_path: Path) -> list[RequestLog]:
    """Load request rows from ``requests.jsonl``."""
    return _read_requests_jsonl(requests_path)


def _write_parquet_outputs(
    predictions: list[PostPrediction],
    requests: list[RequestLog],
    output_dir: Path,
) -> None:
    """Write labels and requests parquet files for one pass."""
    _write_parquet(
        output_dir / LABELS_FILENAME,
        [prediction.model_dump() for prediction in predictions],
    )
    _write_parquet(
        output_dir / REQUESTS_PARQUET_FILENAME,
        [request.model_dump() for request in requests],
    )


def _build_pass_results(
    batch_size: int,
    predictions: list[PostPrediction],
    requests: list[RequestLog],
    output_dir: Path,
) -> PassResults:
    """Aggregate pass metrics into one ``PassResults`` payload."""
    prediction_summary = summarize_pass_predictions(predictions)
    request_summary = summarize_pass_requests(requests)
    latency = RequestLatencyMs.model_validate(request_summary["request_latency_ms"])
    n_deadletter = _count_outstanding_deadletters(
        predictions, output_dir / DEADLETTER_FILENAME
    )
    return PassResults(
        batch_size=batch_size,
        n_scored=len(predictions),
        n_deadletter=n_deadletter,
        n_requests=int(request_summary["n_requests"]),
        f1=prediction_summary["f1"],
        accuracy=prediction_summary["accuracy"],
        precision=prediction_summary["precision"],
        recall=prediction_summary["recall"],
        request_latency_ms=latency,
        per_post_latency_ms_p50=prediction_summary["per_post_latency_ms_p50"],
        wall_time_seconds=_read_wall_time_seconds(output_dir / RUNS_FILENAME),
        input_tokens=int(request_summary["input_tokens"]),
        output_tokens=int(request_summary["output_tokens"]),
        estimated_cost_usd=float(request_summary["estimated_cost_usd"]),
        model_versions=list(request_summary["model_versions"]),
        price_source=PRICE_SOURCE,
    )


def _write_results_json(output_dir: Path, results: PassResults) -> None:
    """Write ``results.json`` for one batch-size pass."""
    path = output_dir / RESULTS_FILENAME
    path.write_text(
        json.dumps(results.model_dump(), indent=2) + "\n",
        encoding="utf-8",
    )


def _write_score_histogram(predictions: list[PostPrediction], static_dir: Path) -> Path:
    """Write a probability histogram PNG and return its path."""
    static_dir.mkdir(parents=True, exist_ok=True)
    hist_path = static_dir / HISTOGRAM_FILENAME
    values = [prediction.probability for prediction in predictions]
    figure, axis = plt.subplots()
    axis.hist(values, bins=HISTOGRAM_BINS, range=HISTOGRAM_RANGE)
    axis.set_xlabel("probability")
    axis.set_ylabel("count")
    figure.savefig(hist_path)
    plt.close(figure)
    return hist_path


def _write_results_markdown(output_dir: Path, results: PassResults) -> None:
    """Write per-pass ``RESULTS.md`` with a metrics table and histogram link."""
    histogram_path = f"{STATIC_DIRNAME}/{HISTOGRAM_FILENAME}"
    lines = [
        f"# Batch size {results.batch_size}",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    lines.extend(_results_table_rows(results))
    lines.extend(["", f"![score histogram]({histogram_path})", ""])
    lines.append(_deadletter_line(results.n_deadletter))
    path = output_dir / RESULTS_MARKDOWN_FILENAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _results_table_rows(results: PassResults) -> list[str]:
    """Build markdown table rows for one pass summary."""
    latency = results.request_latency_ms
    rows = [
        ("batch_size", results.batch_size),
        ("n_scored", results.n_scored),
        ("n_deadletter", results.n_deadletter),
        ("n_requests", results.n_requests),
        ("f1", results.f1),
        ("accuracy", results.accuracy),
        ("precision", results.precision),
        ("recall", results.recall),
        ("request_latency_ms_p50", latency.p50),
        ("request_latency_ms_p90", latency.p90),
        ("request_latency_ms_p99", latency.p99),
        ("per_post_latency_ms_p50", results.per_post_latency_ms_p50),
        ("wall_time_seconds", results.wall_time_seconds),
        ("input_tokens", results.input_tokens),
        ("output_tokens", results.output_tokens),
        ("estimated_cost_usd", results.estimated_cost_usd),
        ("model_versions", results.model_versions),
        ("price_source", results.price_source),
    ]
    return [f"| {name} | {value} |" for name, value in rows]


def _deadletter_line(n_deadletter: int) -> str:
    """Return a short deadletter summary sentence for RESULTS markdown."""
    if n_deadletter == 0:
        return "0 deadletters."
    return f"{n_deadletter} deadletters. See deadletter.jsonl."


def _frame_to_tasks(frame: pd.DataFrame) -> list[PostTask]:
    """Convert a sample dataframe into scoring tasks."""
    tasks: list[PostTask] = []
    for row in frame.itertuples(index=False):
        tasks.append(
            PostTask(
                source_row_id=str(getattr(row, ROW_ID_COLUMN)),
                text=str(getattr(row, TEXT_COLUMN)),
                gold_label=int(getattr(row, GOLD_LABEL_COLUMN)),
            )
        )
    return tasks


def _read_predictions_jsonl(path: Path) -> list[PostPrediction]:
    """Load prediction records from a JSONL file."""
    if not path.is_file():
        return []
    records: list[PostPrediction] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(PostPrediction.model_validate_json(line))
    return records


def _read_requests_jsonl(path: Path) -> list[RequestLog]:
    """Load request log records from a JSONL file."""
    if not path.is_file():
        return []
    records: list[RequestLog] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(RequestLog.model_validate_json(line))
    return records


def _dedupe_predictions(predictions: list[PostPrediction]) -> list[PostPrediction]:
    """Keep the latest prediction per ``source_row_id``, sorted by row id."""
    latest: dict[str, PostPrediction] = {}
    for prediction in predictions:
        latest[prediction.source_row_id] = prediction
    return sorted(latest.values(), key=lambda item: int(item.source_row_id))


def _write_parquet(path: Path, rows: list[dict[str, object]]) -> None:
    """Write a list of row dicts to parquet."""
    frame = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)


def _count_outstanding_deadletters(
    predictions: list[PostPrediction], deadletter_path: Path
) -> int:
    """Count deadletter rows for posts that never received a prediction."""
    scored_ids = {prediction.source_row_id for prediction in predictions}
    if not deadletter_path.is_file():
        return 0
    outstanding: set[str] = set()
    for line in deadletter_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row_id = str(json.loads(line)["source_row_id"])
        if row_id not in scored_ids:
            outstanding.add(row_id)
    return len(outstanding)


def _read_wall_time_seconds(runs_path: Path) -> float:
    """Sum ``wall_time_seconds`` across all lines of ``runs.jsonl``."""
    if not runs_path.is_file():
        return 0.0
    total = 0.0
    for line in runs_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        total += float(payload["wall_time_seconds"])
    return total


if __name__ == "__main__":
    main()
