"""Batch, retry, skip-seen, and deadletter jobs for scoring engines.

Run from the experiment folder:

    uv run python -c "from shared.engine_loop import label_records; print(label_records.__name__)"
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from shared.records import PredictionRecord


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
    """Score unseen tasks and write labels.parquet plus deadletter.jsonl."""
    raise NotImplementedError
