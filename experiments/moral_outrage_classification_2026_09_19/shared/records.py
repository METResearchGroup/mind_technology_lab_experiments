"""Shared prediction record written by every scoring engine.

Run from the experiment folder:

    uv run python -c "from shared.records import PredictionRecord; print(PredictionRecord.__name__)"
"""

from pydantic import BaseModel


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
