"""Perspective AnalyzeComment engine for MORAL_OUTRAGE.

Run from the experiment folder:

    uv run python -c "from models.perspective_api import PerspectiveApiEngine; print(PerspectiveApiEngine.__name__)"
"""

from shared.records import PredictionRecord


class MoralOutrageAttributeRejected(Exception):
    """AnalyzeComment rejected the MORAL_OUTRAGE attribute."""


class PerspectiveApiEngine:
    """Score one post with Perspective MORAL_OUTRAGE."""

    def label_one(self, text: str) -> PredictionRecord:
        raise NotImplementedError

    def label_records(self, tasks: list[object], output_dir: object) -> list[PredictionRecord]:
        raise NotImplementedError
