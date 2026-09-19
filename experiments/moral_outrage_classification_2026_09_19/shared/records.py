"""Shared prediction record written by every scoring engine.

Run from the experiment folder:

    uv run python -c "from shared.records import PredictionRecord; print(PredictionRecord.__name__)"
"""

from pydantic import BaseModel

MODEL_NAME_JEV = "Jev"
MODEL_NAME_PERSPECTIVE = "Perspective API"
BEDROCK_MODEL_IDS = (
    "us.openai.gpt-5.6-luna",
    "us.openai.gpt-5.6-terra",
    "us.anthropic.claude-sonnet-5",
    "qwen.qwen3-32b-v1:0",
    "deepseek.v3-v1:0",
)
BEDROCK_MODEL_NAMES = tuple(f"Bedrock:{model_id}" for model_id in BEDROCK_MODEL_IDS)
POSITIVE_PROBABILITY_THRESHOLD = 0.5


class PredictionRecord(BaseModel):
    """One scored row. Bodies stay stubbed until tests exist."""

    source_row_id: str
    text: str
    gold_label: int
    model_name: str
    probability: float | None
    binary_label: int
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float
