"""TypeSafe Jev engine for Brady moral outrage scores.

Run from the experiment folder:

    uv run python -c "from models.jev import JevEngine; print(JevEngine.__name__)"
"""

from pathlib import Path
from typing import Protocol

from typesafe_sdk import Noul, TypeSafeClient

from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS
from shared.engine_loop import LabelTask, label_records
from shared.metrics import binary_label_from_probability
from shared.pricing import estimate_cost_usd
from shared.records import MODEL_NAME_JEV, PredictionRecord
from shared.secrets import load_typesafe_api_key
from shared.timer import timed

JEV_MODEL_ID = "jev-latest"
JEV_QUESTION_ID = "moral_outrage"
DEFAULT_BATCH_SIZE = 8
DEFAULT_MAX_LABEL_RETRIES = 3


class TypeSafeSystemOneClient(Protocol):
    def system_one(self, state: object, questions: object, model: str) -> object:
        """Run one TypeSafe System One request."""


class JevEngine:
    """Score one post with jev-latest via typesafe-sdk."""

    def __init__(self, client: TypeSafeSystemOneClient | None = None) -> None:
        self._client = client
        self.model_name = MODEL_NAME_JEV

    def label_one(self, text: str) -> PredictionRecord:
        """Score one post text with Jev."""
        client = self._client if self._client is not None else self._live_client()
        response, latency_ms = _system_one(client, text)
        answer = response.answers[JEV_QUESTION_ID]
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        probability = float(answer.noul)
        return PredictionRecord(
            source_row_id="",
            text=text,
            gold_label=0,
            model_name=MODEL_NAME_JEV,
            probability=probability,
            binary_label=binary_label_from_probability(probability),
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost_usd(
                MODEL_NAME_JEV, input_tokens, output_tokens
            ),
        )

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
        record = self.label_one(task.text)
        return record.model_copy(
            update={
                "source_row_id": task.source_row_id,
                "text": task.text,
                "gold_label": task.gold_label,
            }
        )

    def _live_client(self) -> TypeSafeClient:
        return TypeSafeClient(api_key=load_typesafe_api_key(), model=JEV_MODEL_ID)


@timed
def _system_one(client: TypeSafeSystemOneClient, text: str) -> object:
    return client.system_one(
        state=text,
        questions={
            JEV_QUESTION_ID: Noul(instructions=BRADY_MORAL_OUTRAGE_INSTRUCTIONS)
        },
        model=JEV_MODEL_ID,
    )
