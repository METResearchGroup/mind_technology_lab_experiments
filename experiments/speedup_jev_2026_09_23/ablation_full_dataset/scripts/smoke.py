"""Smoke test the first 80 shuffled posts at batch sizes 60 and 80.

Run from the experiment folder:

    uv run python ablation_full_dataset/scripts/smoke.py
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from models.batched_jev import BatchResult, build_live_scorer  # noqa: E402
from shared.batch_runner import (  # noqa: E402
    PREDICTIONS_FILENAME,
    REQUESTS_FILENAME,
    run_pass,
)
from shared.full_dataset import SHUFFLE_SEED, shuffled_tasks  # noqa: E402
from shared.metrics import latency_percentiles  # noqa: E402
from shared.rate_limiter import (  # noqa: E402
    MAX_REQUEST_STARTS_PER_MINUTE,
    RequestStartLimiter,
)
from shared.records import PassSummary, PostTask, RequestLog  # noqa: E402
from shared.secrets import load_typesafe_api_key  # noqa: E402

SMOKE_BATCH_SIZES: tuple[int, ...] = (60, 80)
SMOKE_POST_COUNT = 80
ABLATION_ROOT = EXPERIMENT_ROOT / "ablation_full_dataset"
SMOKE_OUTPUT_ROOT = ABLATION_ROOT / "outputs" / "smoke"
TABLE_HEADER = (
    "batch_size answered deadletter requests "
    "p50_request_ms input_tokens estimated_cost_usd"
)
COST_DECIMAL_PLACES = 6
LATENCY_DECIMAL_PLACES = 1


@dataclass(frozen=True)
class SmokeTableRow:
    """One printed smoke-test summary row."""

    batch_size: int
    answered: int
    deadletter: int
    requests: int
    p50_request_ms: float
    input_tokens: int
    estimated_cost_usd: float


def main() -> None:
    """Score the smoke slice and print one summary row per batch size."""
    tasks = _load_smoke_tasks()
    scorer = build_live_scorer(load_typesafe_api_key())
    limiter = RequestStartLimiter(MAX_REQUEST_STARTS_PER_MINUTE)
    rows = [
        _run_smoke_batch(batch_size, tasks, scorer, limiter)
        for batch_size in SMOKE_BATCH_SIZES
    ]
    _print_table(rows)
    if not _smoke_passed(rows):
        raise SystemExit(1)


def _load_smoke_tasks() -> list[PostTask]:
    """Return the first ``SMOKE_POST_COUNT`` posts in shuffle order."""
    tasks = shuffled_tasks(SHUFFLE_SEED)
    return tasks[:SMOKE_POST_COUNT]


def _clear_smoke_output(batch_size: int) -> None:
    """Delete an earlier smoke output folder so requests are resent."""
    output_dir = _smoke_output_dir(batch_size)
    if output_dir.exists():
        shutil.rmtree(output_dir)


def _smoke_output_dir(batch_size: int) -> Path:
    """Return the output directory for one smoke batch size."""
    return SMOKE_OUTPUT_ROOT / f"batch_{batch_size}"


def _run_smoke_batch(
    batch_size: int,
    tasks: list[PostTask],
    scorer: Callable[[list[str]], BatchResult],
    limiter: RequestStartLimiter,
) -> SmokeTableRow:
    """Run one smoke pass and build its summary row from ``requests.jsonl``."""
    _clear_smoke_output(batch_size)
    output_dir = _smoke_output_dir(batch_size)
    summary = run_pass(tasks, batch_size, output_dir, scorer, limiter)
    request_logs = _read_request_logs(output_dir / REQUESTS_FILENAME)
    answered = _count_predictions(output_dir / PREDICTIONS_FILENAME)
    return _build_table_row(batch_size, summary, request_logs, answered)


def _build_table_row(
    batch_size: int,
    summary: PassSummary,
    request_logs: list[RequestLog],
    answered: int,
) -> SmokeTableRow:
    """Aggregate request-log metrics into one smoke table row."""
    latencies = [log.request_latency_ms for log in request_logs]
    p50_request_ms = latency_percentiles(latencies)["p50"]
    input_tokens = sum(log.input_tokens for log in request_logs)
    estimated_cost_usd = sum(log.estimated_cost_usd for log in request_logs)
    return SmokeTableRow(
        batch_size=batch_size,
        answered=answered,
        deadletter=summary.n_deadletter,
        requests=len(request_logs),
        p50_request_ms=p50_request_ms,
        input_tokens=input_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )


def _read_request_logs(requests_path: Path) -> list[RequestLog]:
    """Load request rows written by ``run_pass``."""
    if not requests_path.is_file():
        return []
    logs: list[RequestLog] = []
    for line in requests_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            logs.append(RequestLog.model_validate_json(line))
    return logs


def _count_predictions(predictions_path: Path) -> int:
    """Count scored posts in ``predictions.jsonl``."""
    if not predictions_path.is_file():
        return 0
    count = 0
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            count += 1
    return count


def _print_table(rows: list[SmokeTableRow]) -> None:
    """Print the smoke summary table."""
    print(TABLE_HEADER)
    for row in rows:
        print(_format_row(row))


def _format_row(row: SmokeTableRow) -> str:
    """Format one smoke summary row for stdout."""
    cost = format(row.estimated_cost_usd, f".{COST_DECIMAL_PLACES}f")
    latency = format(row.p50_request_ms, f".{LATENCY_DECIMAL_PLACES}f")
    return (
        f"{row.batch_size} {row.answered} {row.deadletter} {row.requests} "
        f"{latency} {row.input_tokens} {cost}"
    )


def _smoke_passed(rows: list[SmokeTableRow]) -> bool:
    """Return whether every batch size answered all smoke posts."""
    return all(row.answered >= SMOKE_POST_COUNT for row in rows)


if __name__ == "__main__":
    main()
