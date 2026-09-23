"""Run one full Jev pass for a batch size and write pass outputs.

Run from the experiment folder:

    uv run python scripts/run_batch_size.py --batch-size 5
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from pydantic import BaseModel  # noqa: E402

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from models.batched_jev import BatchResult, build_live_scorer  # noqa: E402
from shared.batch_runner import (  # noqa: E402
    DEADLETTER_FILENAME,
    PREDICTIONS_FILENAME,
    REQUESTS_FILENAME,
    RUNS_FILENAME,
    run_pass,
)
from shared.data import load_sample  # noqa: E402
from shared.pricing import PRICE_PAGE_DATE, PRICE_PAGE_URL  # noqa: E402
from shared.rate_limiter import (  # noqa: E402
    MAX_REQUEST_STARTS_PER_MINUTE,
    RequestStartLimiter,
)
from shared.records import PassSummary, PostPrediction, PostTask, RequestLog  # noqa: E402
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
    hist_path = _write_score_histogram(predictions, output_dir / STATIC_DIRNAME)
    _write_results_markdown(output_dir, results, hist_path)


def _parse_batch_size() -> int:
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
    raise NotImplementedError


def _output_dir(batch_size: int) -> Path:
    raise NotImplementedError


def _load_deduped_predictions(predictions_path: Path) -> list[PostPrediction]:
    raise NotImplementedError


def _load_requests(requests_path: Path) -> list[RequestLog]:
    raise NotImplementedError


def _write_parquet_outputs(
    predictions: list[PostPrediction],
    requests: list[RequestLog],
    output_dir: Path,
) -> None:
    raise NotImplementedError


def _build_pass_results(
    batch_size: int,
    predictions: list[PostPrediction],
    requests: list[RequestLog],
    output_dir: Path,
) -> PassResults:
    raise NotImplementedError


def _write_results_json(output_dir: Path, results: PassResults) -> None:
    raise NotImplementedError


def _write_score_histogram(
    predictions: list[PostPrediction], static_dir: Path
) -> Path:
    raise NotImplementedError


def _write_results_markdown(
    output_dir: Path, results: PassResults, hist_path: Path
) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
