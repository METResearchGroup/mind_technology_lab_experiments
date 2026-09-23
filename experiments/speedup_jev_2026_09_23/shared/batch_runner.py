"""Batch grouping and threaded pass runner with retries and deadletters.

Run from the experiment folder:

    uv run python -c "from shared.batch_runner import make_batches; print(make_batches.__name__)"
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from typesafe_sdk import TypeSafeAuthenticationError, TypeSafePermissionDeniedError

from models.batched_jev import BatchResult
from shared.metrics import binary_label_from_probability
from shared.pricing import estimate_jev_cost_usd
from shared.rate_limiter import RequestStartLimiter
from shared.records import PassSummary, PostPrediction, PostTask, RequestLog

WORKER_THREADS = 8
MAX_EXTRA_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)
PROGRESS_FRACTION = 0.1

PREDICTIONS_FILENAME = "predictions.jsonl"
REQUESTS_FILENAME = "requests.jsonl"
DEADLETTER_FILENAME = "deadletter.jsonl"
RUNS_FILENAME = "runs.jsonl"


@dataclass(frozen=True)
class _BatchSuccess:
    batch: tuple[PostTask, ...]
    request_index: int
    result: BatchResult
    attempts: int


@dataclass(frozen=True)
class _BatchFailure:
    batch: tuple[PostTask, ...]
    request_index: int
    error: str
    attempts: int


def make_batches(tasks: list[PostTask], batch_size: int) -> list[list[PostTask]]:
    """Cut tasks sorted by row id into consecutive groups."""
    ordered = sorted(tasks, key=lambda task: int(task.source_row_id))
    batches: list[list[PostTask]] = []
    for start in range(0, len(ordered), batch_size):
        batches.append(ordered[start : start + batch_size])
    return batches


def run_pass(
    tasks: list[PostTask],
    batch_size: int,
    output_dir: Path,
    scorer: Callable[[list[str]], BatchResult],
    limiter: RequestStartLimiter,
) -> PassSummary:
    """Score pending tasks, write JSONL logs, and return pass counts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC)
    wall_started = time.monotonic()
    pending = _pending_tasks(tasks, output_dir)
    batches = make_batches(pending, batch_size)
    counts = _run_batches(batches, batch_size, output_dir, scorer, limiter)
    wall_seconds = time.monotonic() - wall_started
    summary = PassSummary(
        batch_size=batch_size,
        n_requests=len(batches),
        n_scored=counts["n_scored"],
        n_deadletter=counts["n_deadletter"],
        wall_time_seconds=wall_seconds,
    )
    _append_run_log(output_dir, started_at, summary)
    _print_final_line(summary)
    return summary


def _pending_tasks(tasks: list[PostTask], output_dir: Path) -> list[PostTask]:
    seen = _seen_source_row_ids(output_dir / PREDICTIONS_FILENAME)
    return [task for task in tasks if task.source_row_id not in seen]


def _seen_source_row_ids(predictions_path: Path) -> set[str]:
    if not predictions_path.is_file():
        return set()
    seen: set[str] = set()
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        seen.add(str(payload["source_row_id"]))
    return seen


def _run_batches(
    batches: list[list[PostTask]],
    batch_size: int,
    output_dir: Path,
    scorer: Callable[[list[str]], BatchResult],
    limiter: RequestStartLimiter,
) -> dict[str, int]:
    if not batches:
        return {"n_scored": 0, "n_deadletter": 0}
    n_scored = 0
    n_deadletter = 0
    progress_step = _progress_step(len(batches))
    with ThreadPoolExecutor(max_workers=WORKER_THREADS) as executor:
        futures = _submit_batches(executor, batches, scorer, limiter)
        completed = 0
        try:
            for future in as_completed(futures):
                outcome = future.result()
                scored, deadlettered = _write_outcome(
                    outcome, batch_size, output_dir
                )
                n_scored += scored
                n_deadletter += deadlettered
                completed += 1
                if _should_report_progress(completed, len(batches), progress_step):
                    _print_progress(completed, len(batches), batch_size)
        except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError):
            _cancel_futures(futures)
            raise
    return {"n_scored": n_scored, "n_deadletter": n_deadletter}


def _submit_batches(
    executor: ThreadPoolExecutor,
    batches: list[list[PostTask]],
    scorer: Callable[[list[str]], BatchResult],
    limiter: RequestStartLimiter,
) -> list[Future[_BatchSuccess | _BatchFailure]]:
    futures: list[Future[_BatchSuccess | _BatchFailure]] = []
    for request_index, batch in enumerate(batches):
        future = executor.submit(
            _score_batch_job, tuple(batch), request_index, scorer, limiter
        )
        futures.append(future)
    return futures


def _score_batch_job(
    batch: tuple[PostTask, ...],
    request_index: int,
    scorer: Callable[[list[str]], BatchResult],
    limiter: RequestStartLimiter,
) -> _BatchSuccess | _BatchFailure:
    texts = [task.text for task in batch]
    last_error = "unknown"
    total_attempts = MAX_EXTRA_ATTEMPTS + 1
    for attempt in range(1, total_attempts + 1):
        limiter.wait()
        try:
            result = scorer(texts)
            return _BatchSuccess(batch, request_index, result, attempt)
        except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError):
            raise
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt <= MAX_EXTRA_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[attempt - 1])
                continue
            return _BatchFailure(batch, request_index, last_error, attempt)
    return _BatchFailure(batch, request_index, last_error, total_attempts)


def _write_outcome(
    outcome: _BatchSuccess | _BatchFailure,
    batch_size: int,
    output_dir: Path,
) -> tuple[int, int]:
    if isinstance(outcome, _BatchSuccess):
        _write_success(outcome, batch_size, output_dir)
        return len(outcome.batch), 0
    _write_failure(outcome, output_dir)
    return 0, len(outcome.batch)


def _write_success(
    outcome: _BatchSuccess, batch_size: int, output_dir: Path
) -> None:
    predictions = _build_predictions(outcome, batch_size)
    request_log = _build_request_log(outcome, batch_size)
    predictions_path = output_dir / PREDICTIONS_FILENAME
    requests_path = output_dir / REQUESTS_FILENAME
    for prediction in predictions:
        _append_jsonl(predictions_path, prediction)
    _append_jsonl(requests_path, request_log)


def _write_failure(outcome: _BatchFailure, output_dir: Path) -> None:
    deadletter_path = output_dir / DEADLETTER_FILENAME
    for task in outcome.batch:
        line = {
            "source_row_id": task.source_row_id,
            "request_index": outcome.request_index,
            "error": outcome.error,
            "attempts": outcome.attempts,
        }
        _append_json_line(deadletter_path, line)


def _build_predictions(
    outcome: _BatchSuccess, batch_size: int
) -> list[PostPrediction]:
    n_posts = len(outcome.batch)
    per_post_latency = outcome.result.latency_ms / n_posts
    predictions: list[PostPrediction] = []
    for position, (task, probability) in enumerate(
        zip(outcome.batch, outcome.result.probabilities, strict=True)
    ):
        predictions.append(
            PostPrediction(
                source_row_id=task.source_row_id,
                text=task.text,
                gold_label=task.gold_label,
                batch_size=batch_size,
                request_index=outcome.request_index,
                position_in_request=position,
                n_posts_in_request=n_posts,
                probability=probability,
                binary_label=binary_label_from_probability(probability),
                request_latency_ms=outcome.result.latency_ms,
                per_post_latency_ms=per_post_latency,
                request_input_tokens=outcome.result.input_tokens,
                request_output_tokens=outcome.result.output_tokens,
                model_version=outcome.result.model_version,
                attempts=outcome.attempts,
            )
        )
    return predictions


def _build_request_log(outcome: _BatchSuccess, batch_size: int) -> RequestLog:
    result = outcome.result
    n_posts = len(outcome.batch)
    return RequestLog(
        batch_size=batch_size,
        request_index=outcome.request_index,
        n_posts_in_request=n_posts,
        request_latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost_usd=estimate_jev_cost_usd(
            result.input_tokens, result.output_tokens
        ),
        model_version=result.model_version,
        attempts=outcome.attempts,
    )


def _append_jsonl(path: Path, record: PostPrediction | RequestLog) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")


def _append_json_line(path: Path, payload: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _append_run_log(
    output_dir: Path, started_at: datetime, summary: PassSummary
) -> None:
    line = {
        "batch_size": summary.batch_size,
        "started_at": started_at.isoformat(),
        "wall_time_seconds": summary.wall_time_seconds,
        "n_requests": summary.n_requests,
        "n_scored": summary.n_scored,
        "n_deadletter": summary.n_deadletter,
    }
    _append_json_line(output_dir / RUNS_FILENAME, line)


def _progress_step(n_batches: int) -> int:
    if n_batches == 0:
        return 1
    return max(1, int(n_batches * PROGRESS_FRACTION))


def _should_report_progress(
    completed: int, total: int, progress_step: int
) -> bool:
    if completed == total:
        return True
    return completed % progress_step == 0


def _print_progress(completed: int, total: int, batch_size: int) -> None:
    print(f"progress batch_size={batch_size} completed={completed}/{total}")


def _print_final_line(summary: PassSummary) -> None:
    print(
        "batch_size="
        f"{summary.batch_size} scored={summary.n_scored} "
        f"deadletter={summary.n_deadletter} requests={summary.n_requests}"
    )


def _cancel_futures(
    futures: list[Future[_BatchSuccess | _BatchFailure]],
) -> None:
    for future in futures:
        future.cancel()
