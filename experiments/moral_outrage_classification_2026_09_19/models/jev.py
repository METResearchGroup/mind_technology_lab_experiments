"""TypeSafe Jev engine for Brady moral outrage scores.

Run from the experiment folder:

    uv run python -c "from models.jev import JevEngine; print(JevEngine.__name__)"
"""

from shared.records import PredictionRecord


class JevEngine:
    """Score one post with jev-latest via typesafe-sdk."""

    def label_one(self, text: str) -> PredictionRecord:
        raise NotImplementedError

    def label_records(self, tasks: list[object], output_dir: object) -> list[PredictionRecord]:
        raise NotImplementedError
