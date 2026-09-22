"""Batch, retry, skip-seen, and deadletter jobs for scoring engines.

Run from the experiment folder:

    uv run python -c "from shared.engine_loop import label_records; print(label_records.__name__)"
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from shared.records import PredictionRecord

LABELS_FILENAME = "labels.parquet"
DEADLETTER_FILENAME = "deadletter.jsonl"
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
DEFAULT_MAX_LABEL_RETRIES = 3


class FatalLabelError(Exception):
    """Stop the job. Do not deadletter and continue."""


@dataclass(frozen=True)
class LabelTask:
    source_row_id: str
    text: str
    gold_label: int


def label_records(
    tasks: list[LabelTask],
    label_one: Callable[[LabelTask], PredictionRecord],
    output_dir: Path,
    batch_size: int,
    max_label_retries: int,
) -> list[PredictionRecord]:
    """Score unseen tasks and write labels.parquet plus deadletter.jsonl.

    Parameters
    ----------
    tasks
        Rows to score.
    label_one
        Scores one task.
    output_dir
        Directory for labels.parquet and deadletter.jsonl.
    batch_size
        Chunk size.
    max_label_retries
        Extra attempts after the first. 3 means 4 tries.

    Returns
    -------
    list[PredictionRecord]
        Newly written successful records.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pending = [task for task in tasks if task.source_row_id not in _seen_ids(output_dir)]
    written: list[PredictionRecord] = []
    print(
        f"label_records dir={output_dir} seen={len(tasks) - len(pending)} "
        f"pending={len(pending)}",
        flush=True,
    )
    for batch_index, chunk in enumerate(_batched(pending, batch_size)):
        batch_records = _label_chunk(
            chunk, label_one, output_dir, batch_index, max_label_retries
        )
        written.extend(batch_records)
        print(
            f"batch {batch_index} scored={len(batch_records)} "
            f"chunk={len(chunk)} dir={output_dir.name}",
            flush=True,
        )
    return written


def _batched(tasks: list[LabelTask], batch_size: int) -> Iterator[list[LabelTask]]:
    for start in range(0, len(tasks), batch_size):
        yield tasks[start : start + batch_size]


def _seen_ids(output_dir: Path) -> set[str]:
    labels_path = output_dir / LABELS_FILENAME
    if not labels_path.is_file():
        return set()
    frame = pd.read_parquet(labels_path, columns=["source_row_id"])
    return set(frame["source_row_id"].astype(str))


def _label_chunk(
    chunk: list[LabelTask],
    label_one: Callable[[LabelTask], PredictionRecord],
    output_dir: Path,
    batch_index: int,
    max_label_retries: int,
) -> list[PredictionRecord]:
    last_error = "unknown"
    total_attempts = max_label_retries + 1
    for attempt in range(1, total_attempts + 1):
        try:
            records = [label_one(task) for task in chunk]
        except FatalLabelError:
            raise
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if _is_retryable(exc) and attempt < total_attempts:
                continue
            _write_deadletter(output_dir, chunk, last_error, attempt, batch_index)
            return []
        _append_labels(output_dir, records)
        return records
    _write_deadletter(output_dir, chunk, last_error, total_attempts, batch_index)
    return []


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    return http_status_code(exc) in RETRYABLE_STATUS_CODES


def http_status_code(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        metadata = response.get("ResponseMetadata", {})
        if isinstance(metadata, dict):
            http_status = metadata.get("HTTPStatusCode")
            if isinstance(http_status, int):
                return http_status
        return None
    response_status = getattr(response, "status_code", None)
    if isinstance(response_status, int):
        return response_status
    return None


def _append_labels(output_dir: Path, records: list[PredictionRecord]) -> None:
    labels_path = output_dir / LABELS_FILENAME
    new_frame = pd.DataFrame([record.model_dump() for record in records])
    if labels_path.is_file():
        existing = pd.read_parquet(labels_path)
        frame = pd.concat([existing, new_frame], ignore_index=True)
    else:
        frame = new_frame
    frame.to_parquet(labels_path, index=False)


def _write_deadletter(
    output_dir: Path,
    chunk: list[LabelTask],
    error: str,
    attempts: int,
    batch_index: int,
) -> None:
    deadletter_path = output_dir / DEADLETTER_FILENAME
    with deadletter_path.open("a", encoding="utf-8") as handle:
        for task in chunk:
            line = {
                "source_row_id": task.source_row_id,
                "error": error,
                "attempts": attempts,
                "batch_index": batch_index,
            }
            handle.write(json.dumps(line) + "\n")
