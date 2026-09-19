"""TypeSafe Jev engine for Brady moral outrage scores.

Run from the experiment folder:

    uv run python -c "from models.jev import JevEngine; print(JevEngine.__name__)"
"""

from typing import Protocol

from shared.engine_loop import LabelTask
from shared.records import MODEL_NAME_JEV, PredictionRecord

JEV_MODEL_ID = "jev-latest"
JEV_QUESTION_ID = "moral_outrage"
DEFAULT_BATCH_SIZE = 8


class TypeSafeSystemOneClient(Protocol):
    def system_one(self, state: object, questions: object, model: str) -> object:
        """Run one TypeSafe System One request."""


class JevEngine:
    """Score one post with jev-latest via typesafe-sdk."""

    def __init__(self, client: TypeSafeSystemOneClient | None = None) -> None:
        self._client = client
        self.model_name = MODEL_NAME_JEV

    def label_one(self, text: str) -> PredictionRecord:
        raise NotImplementedError

    def label_records(
        self, tasks: list[LabelTask], output_dir: object
    ) -> list[PredictionRecord]:
        raise NotImplementedError
