"""Run smoke test on first 40 posts at batch sizes 5 and 40.

Run from the experiment folder:

    uv run python scripts/smoke.py
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.batch_runner import REQUESTS_FILENAME, run_pass  # noqa: E402
from shared.data import load_sample  # noqa: E402
from shared.metrics import latency_percentiles  # noqa: E402
from shared.rate_limiter import (  # noqa: E402
    MAX_REQUEST_STARTS_PER_MINUTE,
    RequestStartLimiter,
)
from shared.records import PassSummary, PostTask, RequestLog  # noqa: E402
from shared.secrets import load_typesafe_api_key  # noqa: E402

SMOKE_BATCH_SIZES: tuple[int, ...] = (5, 40)
SMOKE_POST_COUNT = 40
SMOKE_OUTPUT_ROOT = EXPERIMENT_ROOT / "outputs" / "smoke"
TABLE_HEADER = (
    "batch_size answered deadletter requests "
    "p50_request_ms input_tokens estimated_cost_usd"
)
ROW_ID_COLUMN = "source_row_id"
TEXT_COLUMN = "text"
GOLD_LABEL_COLUMN = "gold_label"
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
    raise NotImplementedError


def _load_smoke_tasks() -> list[PostTask]:
    raise NotImplementedError


def _clear_smoke_output(batch_size: int) -> None:
    raise NotImplementedError


def _smoke_output_dir(batch_size: int) -> Path:
    return SMOKE_OUTPUT_ROOT / f"batch_{batch_size}"


def _run_smoke_batch(
    batch_size: int,
    tasks: list[PostTask],
    scorer: object,
    limiter: RequestStartLimiter,
) -> SmokeTableRow:
    raise NotImplementedError


def _build_table_row(
    batch_size: int,
    summary: PassSummary,
    request_logs: list[RequestLog],
    answered: int,
) -> SmokeTableRow:
    raise NotImplementedError


def _read_request_logs(requests_path: Path) -> list[RequestLog]:
    raise NotImplementedError


def _count_predictions(predictions_path: Path) -> int:
    raise NotImplementedError


def _print_table(rows: list[SmokeTableRow]) -> None:
    raise NotImplementedError


def _format_row(row: SmokeTableRow) -> str:
    raise NotImplementedError


def _smoke_passed(rows: list[SmokeTableRow]) -> bool:
    raise NotImplementedError


def _frame_to_tasks(frame: object) -> list[PostTask]:
    raise NotImplementedError


if __name__ == "__main__":
    main()
