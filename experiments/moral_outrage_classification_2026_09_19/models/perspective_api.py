"""Perspective AnalyzeComment engine for MORAL_OUTRAGE.

Run from the experiment folder:

    uv run python -c "from models.perspective_api import PerspectiveApiEngine; print(PerspectiveApiEngine.__name__)"
"""

from collections.abc import Callable

from shared.engine_loop import LabelTask
from shared.records import MODEL_NAME_PERSPECTIVE, PredictionRecord

ANALYZE_COMMENT_URL = (
    "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
)
MORAL_OUTRAGE_ATTRIBUTE = "MORAL_OUTRAGE"
DEFAULT_BATCH_SIZE = 1
MIN_SECONDS_BETWEEN_CALLS = 1.0


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
        raise NotImplementedError

    def label_records(
        self, tasks: list[LabelTask], output_dir: object
    ) -> list[PredictionRecord]:
        raise NotImplementedError
