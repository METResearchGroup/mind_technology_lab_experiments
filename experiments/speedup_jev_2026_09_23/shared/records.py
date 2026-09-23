"""Pydantic models for batch scoring tasks, predictions, and request logs.

Run from the experiment folder:

    uv run python -c "from shared.records import PostTask; print(PostTask.__name__)"
"""

from __future__ import annotations

from pydantic import BaseModel


class PostTask(BaseModel):
    """One post to score in a batch pass."""

    source_row_id: str
    text: str
    gold_label: int


class PostPrediction(BaseModel):
    """One scored post with shared request metadata."""

    source_row_id: str
    text: str
    gold_label: int
    batch_size: int
    request_index: int
    position_in_request: int
    n_posts_in_request: int
    probability: float
    binary_label: int
    request_latency_ms: float
    per_post_latency_ms: float
    request_input_tokens: int
    request_output_tokens: int
    model_version: str
    attempts: int


class RequestLog(BaseModel):
    """One batched API request."""

    batch_size: int
    request_index: int
    n_posts_in_request: int
    request_latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    model_version: str
    attempts: int


class PassSummary(BaseModel):
    """Counts and wall time for one batch-size pass."""

    batch_size: int
    n_requests: int
    n_scored: int
    n_deadletter: int
    wall_time_seconds: float
