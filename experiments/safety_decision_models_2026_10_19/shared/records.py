"""Example and prediction record types plus the DecisionScorer protocol.

Run from the experiment folder:

    uv run python -c "from shared.records import ExampleRecord; print(ExampleRecord.__name__)"
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field


class ExampleRecord(BaseModel):
    """One row from a dataset loader."""

    example_id: str
    dataset: str
    split: str
    text: str
    gold_labels: dict[str, bool | int | float] | str
    harm_category: str | None = None
    is_benign_known: bool = False
    metadata: dict[str, str | bool] = Field(default_factory=dict)


class QuestionItem(BaseModel):
    """One question in a template, matching the public harness shape."""

    type: str
    instructions: Any
    criteria: Any = None


class QuestionSpec(BaseModel):
    """Template loaded from data/templates/{dataset}.json."""

    questions: dict[str, QuestionItem]


class PredictionRecord(BaseModel):
    """One scored row from a DecisionScorer."""

    example_id: str
    arm: str
    model_version: str
    template_version: str
    probability: float | None = None
    band: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    billed_units: float = 0.0
    error_status: str | None = None


class DecisionScorer(Protocol):
    """Score example rows with one question template."""

    def score(
        self, records: list[ExampleRecord], question: QuestionSpec
    ) -> list[PredictionRecord]: ...
