"""File-backed Perspective engine that returns stored MORAL_OUTRAGE labels.

Run from the experiment folder:

    uv run python -c "from models.perspective_api import PerspectiveApiEngine; print(PerspectiveApiEngine.__name__)"
"""

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from shared.data import download_perspective_labels_csv, load_perspective_labels_frame
from shared.engine_loop import LabelTask, label_records
from shared.metrics import binary_label_from_probability
from shared.pricing import estimate_cost_usd
from shared.records import MODEL_NAME_PERSPECTIVE, PredictionRecord
from shared.timer import timed

DEFAULT_BATCH_SIZE = 1
DEFAULT_MAX_LABEL_RETRIES = 3


class MissingPerspectiveLabel(Exception):
    """The stored Perspective file has no non-empty pred_label for this row."""


class PerspectiveApiEngine:
    """Return a stored Perspective label for one post."""

    def __init__(
        self,
        http_post: Callable[..., object] | None = None,
        api_key: str | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._http_post = http_post
        self._api_key = api_key
        self._sleeper = sleeper
        self.model_name = MODEL_NAME_PERSPECTIVE
        self._by_source_row_id: dict[str, float] | None = None
        self._by_text: dict[str, float] | None = None

    def label_one(self, text: str) -> PredictionRecord:
        """Return the stored Perspective label for this exact text."""
        self._ensure_lookups()
        probability, latency_ms = _lookup_probability(self._by_text, text)
        return _record_from_probability(text, "", 0, probability, latency_ms)

    def label_records(
        self, tasks: list[LabelTask], output_dir: object
    ) -> list[PredictionRecord]:
        """Score tasks through the shared skip-seen loop."""
        return label_records(
            tasks,
            self._label_task,
            Path(str(output_dir)),
            DEFAULT_BATCH_SIZE,
            DEFAULT_MAX_LABEL_RETRIES,
        )

    def _label_task(self, task: LabelTask) -> PredictionRecord:
        self._ensure_lookups()
        probability, latency_ms = _lookup_probability(
            self._by_source_row_id, task.source_row_id
        )
        return _record_from_probability(
            task.text, task.source_row_id, task.gold_label, probability, latency_ms
        )

    def _ensure_lookups(self) -> None:
        if self._by_source_row_id is not None and self._by_text is not None:
            return
        frame = load_perspective_labels_frame(download_perspective_labels_csv())
        by_source_row_id: dict[str, float] = {}
        by_text: dict[str, float] = {}
        for row in frame.itertuples(index=False):
            if pd.isna(row.pred_label):
                continue
            probability = float(row.pred_label)
            source_row_id = str(row.source_row_id)
            by_source_row_id[source_row_id] = probability
            if row.text not in by_text:
                by_text[str(row.text)] = probability
        self._by_source_row_id = by_source_row_id
        self._by_text = by_text


@timed
def _lookup_probability(lookup: dict[str, float] | None, key: str) -> float:
    if lookup is None or key not in lookup:
        raise MissingPerspectiveLabel(
            f"No stored Perspective pred_label for {key!r}"
        )
    return lookup[key]


def _record_from_probability(
    text: str,
    source_row_id: str,
    gold_label: int,
    probability: float,
    latency_ms: float,
) -> PredictionRecord:
    return PredictionRecord(
        source_row_id=source_row_id,
        text=text,
        gold_label=gold_label,
        model_name=MODEL_NAME_PERSPECTIVE,
        probability=probability,
        binary_label=binary_label_from_probability(probability),
        latency_ms=latency_ms,
        input_tokens=None,
        output_tokens=None,
        estimated_cost_usd=estimate_cost_usd(MODEL_NAME_PERSPECTIVE, None, None),
    )
