"""Bedrock Converse engine for the five locked model IDs.

Run from the experiment folder:

    uv run python -c "from models.bedrock import BedrockEngine; print(BedrockEngine.__name__)"
"""

from collections.abc import Callable

from shared.engine_loop import LabelTask
from shared.records import BEDROCK_MODEL_IDS, PredictionRecord

DEFAULT_BATCH_SIZE = 8


class BedrockEngine:
    """Score one post with a single Bedrock model id."""

    def __init__(
        self, model_id: str, converse: Callable[..., object] | None = None
    ) -> None:
        if model_id not in BEDROCK_MODEL_IDS:
            raise ValueError(f"Unsupported Bedrock model id: {model_id}")
        self.model_id = model_id
        self.model_name = f"Bedrock:{model_id}"
        self._converse = converse

    def label_one(self, text: str) -> PredictionRecord:
        raise NotImplementedError

    def label_records(
        self, tasks: list[LabelTask], output_dir: object
    ) -> list[PredictionRecord]:
        raise NotImplementedError
