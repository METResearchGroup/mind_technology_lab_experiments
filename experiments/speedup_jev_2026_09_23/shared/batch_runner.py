"""Batch grouping and threaded pass runner with retries and deadletters.

Run from the experiment folder:

    uv run python -c "from shared.batch_runner import make_batches; print(make_batches.__name__)"
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from shared.records import PassSummary, PostTask
from models.batched_jev import BatchResult
from shared.rate_limiter import RequestStartLimiter

WORKER_THREADS = 8
MAX_EXTRA_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)

PREDICTIONS_FILENAME = "predictions.jsonl"
REQUESTS_FILENAME = "requests.jsonl"
DEADLETTER_FILENAME = "deadletter.jsonl"
RUNS_FILENAME = "runs.jsonl"


def make_batches(tasks: list[PostTask], batch_size: int) -> list[list[PostTask]]:
    """Cut tasks sorted by row id into consecutive groups."""
    raise NotImplementedError


def run_pass(
    tasks: list[PostTask],
    batch_size: int,
    output_dir: Path,
    scorer: Callable[[list[str]], BatchResult],
    limiter: RequestStartLimiter,
) -> PassSummary:
    """Score pending tasks, write JSONL logs, and return pass counts."""
    raise NotImplementedError
