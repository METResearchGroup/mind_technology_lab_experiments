"""Batched Jev engine: state, questions, scoring, and live scorer factory.

Run from the experiment folder:

    uv run python -c "from models.batched_jev import build_questions; print(build_questions.__name__)"
"""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel
from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

JEV_MODEL_ID = "jev-1.13.0"
REQUEST_TIMEOUT_SECONDS = 30.0


class MissingAnswerError(Exception):
    """Raised when a batched response omits a required post answer."""


class BatchResult(BaseModel):
    """Probabilities and usage from one batched request."""

    probabilities: list[float]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model_version: str


def build_state(texts: list[str]) -> dict[str, list[str]]:
    """Return the TypeSafe state mapping for one batch of posts."""
    raise NotImplementedError


def build_questions(n_posts: int) -> dict[str, Noul]:
    """Return one Noul question per post index."""
    raise NotImplementedError


def score_batch(client: TypeSafeClient, texts: list[str]) -> BatchResult:
    """Send one timed batched request and return per-post probabilities."""
    raise NotImplementedError


def build_client(api_key: str) -> TypeSafeClient:
    """Build a TypeSafe client with SDK retries disabled."""
    raise NotImplementedError


def build_live_scorer(api_key: str) -> Callable[[list[str]], BatchResult]:
    """Return a scorer that keeps one client per worker thread."""
    raise NotImplementedError
