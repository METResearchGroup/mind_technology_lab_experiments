"""Perspective AnalyzeComment engine for MORAL_OUTRAGE.

Run from the experiment folder:

    uv run python -c "from models.perspective_api import PerspectiveApiEngine; print(PerspectiveApiEngine.__name__)"
"""

from collections.abc import Callable
from pathlib import Path

import requests

from shared.engine_loop import LabelTask, label_records
from shared.metrics import binary_label_from_probability
from shared.pricing import estimate_cost_usd
from shared.records import MODEL_NAME_PERSPECTIVE, PredictionRecord
from shared.secrets import load_google_api_key
from shared.timer import timed

ANALYZE_COMMENT_URL = (
    "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
)
MORAL_OUTRAGE_ATTRIBUTE = "MORAL_OUTRAGE"
DEFAULT_BATCH_SIZE = 1
DEFAULT_MAX_LABEL_RETRIES = 3
MIN_SECONDS_BETWEEN_CALLS = 1.0
REJECTED_STATUS_CODES = frozenset({400, 404})


class MoralOutrageAttributeRejected(Exception):
    """AnalyzeComment rejected the MORAL_OUTRAGE attribute."""


class PerspectiveApiEngine:
    """Score one post with Perspective MORAL_OUTRAGE."""

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

    def label_one(self, text: str) -> PredictionRecord:
        """Score one post text with Perspective MORAL_OUTRAGE."""
        http_post = self._http_post if self._http_post is not None else requests.post
        api_key = self._api_key if self._api_key is not None else load_google_api_key()
        sleeper = self._sleeper if self._sleeper is not None else _sleep
        response, latency_ms = _analyze_comment(http_post, api_key, text)
        _raise_if_attribute_rejected(response)
        probability = _read_moral_outrage_score(response)
        sleeper(MIN_SECONDS_BETWEEN_CALLS)
        return PredictionRecord(
            source_row_id="",
            text=text,
            gold_label=0,
            model_name=MODEL_NAME_PERSPECTIVE,
            probability=probability,
            binary_label=binary_label_from_probability(probability),
            latency_ms=latency_ms,
            input_tokens=None,
            output_tokens=None,
            estimated_cost_usd=estimate_cost_usd(MODEL_NAME_PERSPECTIVE, None, None),
        )

    def label_records(
        self, tasks: list[LabelTask], output_dir: object
    ) -> list[PredictionRecord]:
        """Score tasks one request at a time through the shared loop."""
        return label_records(
            tasks,
            self._label_task,
            Path(str(output_dir)),
            DEFAULT_BATCH_SIZE,
            DEFAULT_MAX_LABEL_RETRIES,
        )

    def _label_task(self, task: LabelTask) -> PredictionRecord:
        record = self.label_one(task.text)
        return record.model_copy(
            update={
                "source_row_id": task.source_row_id,
                "text": task.text,
                "gold_label": task.gold_label,
            }
        )


def _sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)


@timed
def _analyze_comment(
    http_post: Callable[..., object], api_key: str, text: str
) -> object:
    body = {
        "comment": {"text": text},
        "languages": ["en"],
        "requestedAttributes": {MORAL_OUTRAGE_ATTRIBUTE: {}},
        "doNotStore": True,
    }
    return http_post(
        ANALYZE_COMMENT_URL,
        params={"key": api_key},
        json=body,
    )


def _raise_if_attribute_rejected(response: object) -> None:
    status_code = getattr(response, "status_code", None)
    body_text = getattr(response, "text", "")
    if status_code in REJECTED_STATUS_CODES and MORAL_OUTRAGE_ATTRIBUTE in str(body_text):
        raise MoralOutrageAttributeRejected(
            f"AnalyzeComment rejected {MORAL_OUTRAGE_ATTRIBUTE}"
        )
    if status_code is not None and int(status_code) >= 400:
        raise RuntimeError(f"Perspective HTTP {status_code}: {body_text}")


def _read_moral_outrage_score(response: object) -> float:
    payload = response.json()
    return float(
        payload["attributeScores"][MORAL_OUTRAGE_ATTRIBUTE]["summaryScore"]["value"]
    )
