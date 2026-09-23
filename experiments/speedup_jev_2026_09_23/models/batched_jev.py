"""Batched Jev engine: state, questions, scoring, and live scorer factory.

Run from the experiment folder:

    uv run python -c "from models.batched_jev import build_questions; print(build_questions.__name__)"
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from pydantic import BaseModel
from typesafe_sdk import Noul, RetryPolicy, TypeSafeClient

from shared.brady_definition import BRADY_MORAL_OUTRAGE_DEFINITION
from shared.timer import timed

JEV_MODEL_ID = "jev-1.13.0"
REQUEST_TIMEOUT_SECONDS = 30.0
POSTS_STATE_KEY = "posts"
QUESTION_ID_PREFIX = "post_"


class MissingAnswerError(Exception):
    """Raised when a batched response omits a required post answer."""


class BatchResult(BaseModel):
    """Probabilities and usage from one batched request."""

    probabilities: list[float]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model_version: str


_thread_local = threading.local()


def build_state(texts: list[str]) -> dict[str, list[str]]:
    """Return the TypeSafe state mapping for one batch of posts."""
    return {POSTS_STATE_KEY: list(texts)}


def build_questions(n_posts: int) -> dict[str, Noul]:
    """Return one Noul question per post index."""
    questions: dict[str, Noul] = {}
    for index in range(n_posts):
        question_id = f"{QUESTION_ID_PREFIX}{index}"
        instructions = (
            f"Does `{POSTS_STATE_KEY}[{index}]` express moral outrage? "
            + BRADY_MORAL_OUTRAGE_DEFINITION
        )
        questions[question_id] = Noul(instructions=instructions)
    return questions


def score_batch(client: TypeSafeClient, texts: list[str]) -> BatchResult:
    """Send one timed batched request and return per-post probabilities."""
    state = build_state(texts)
    questions = build_questions(len(texts))
    response, latency_ms = _timed_system_one(client, state, questions)
    probabilities = _extract_probabilities(response, len(texts))
    return BatchResult(
        probabilities=probabilities,
        latency_ms=latency_ms,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model_version=response.model,
    )


def build_client(api_key: str) -> TypeSafeClient:
    """Build a TypeSafe client with SDK retries disabled."""
    return TypeSafeClient(
        api_key=api_key,
        model=JEV_MODEL_ID,
        retry=RetryPolicy(max_retries=0),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


def build_live_scorer(api_key: str) -> Callable[[list[str]], BatchResult]:
    """Return a scorer that keeps one client per worker thread."""
    return lambda texts: score_batch(_thread_client(api_key), texts)


@timed
def _timed_system_one(
    client: TypeSafeClient,
    state: dict[str, list[str]],
    questions: dict[str, Noul],
) -> object:
    return client.system_one(state=state, questions=questions, model=JEV_MODEL_ID)


def _thread_client(api_key: str) -> TypeSafeClient:
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = build_client(api_key)
        _thread_local.client = client
    return client


def _extract_probabilities(response: object, n_posts: int) -> list[float]:
    answers = response.answers
    probabilities: list[float] = []
    for index in range(n_posts):
        question_id = f"{QUESTION_ID_PREFIX}{index}"
        answer = answers.get(question_id)
        if answer is None:
            raise MissingAnswerError(question_id)
        probabilities.append(float(answer.noul))
    return probabilities
