"""Bedrock Converse engine for the five locked model IDs.

Run from the experiment folder:

    uv run python -c "from models.bedrock import BedrockEngine; print(BedrockEngine.__name__)"
"""

from shared.records import PredictionRecord


class BedrockEngine:
    """Score one post with a single Bedrock model id."""

    def __init__(self, model_id: str) -> None:
        raise NotImplementedError

    def label_one(self, text: str) -> PredictionRecord:
        raise NotImplementedError

    def label_records(self, tasks: list[object], output_dir: object) -> list[PredictionRecord]:
        raise NotImplementedError
