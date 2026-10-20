"""Jev DecisionScorer via the TypeSafe API.

Run from the experiment folder:

    uv run python -c "from scorers.jev import JevScorer; print(JevScorer.__name__)"
"""

from __future__ import annotations

import time
from typing import Any

from typesafe_sdk import Choice, Noul, RetryPolicy, Score, TypeSafeClient

from shared.records import ExampleRecord, PredictionRecord, QuestionSpec
from shared.secrets import load_typesafe_api_key

JEV_MODEL_VERSION = "jev-1.13.0"
REQUEST_TIMEOUT_SECONDS = 120.0
MAX_TOKENS_ERROR = "max_tokens_exceeded"


class JevScorer:
    """Score rows with Jev jev-1.13.0."""

    arm = "jev"

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or load_typesafe_api_key()
        self._client = TypeSafeClient(
            api_key=key,
            model=JEV_MODEL_VERSION,
            retry=RetryPolicy(max_retries=0),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    def score(
        self, records: list[ExampleRecord], question: QuestionSpec
    ) -> list[PredictionRecord]:
        """Score each record in its own request."""
        results: list[PredictionRecord] = []
        for record in records:
            results.append(self._score_one(record, question))
        return results

    def _score_one(
        self, record: ExampleRecord, question: QuestionSpec
    ) -> PredictionRecord:
        started = time.perf_counter()
        template_version = _template_version(question)
        try:
            response = self._client.system_one(
                state=record.text,
                questions=_build_ts_questions(question),
                model=JEV_MODEL_VERSION,
            )
        except Exception as exc:  # noqa: BLE001
            status = _jev_error_status(exc)
            latency_ms = (time.perf_counter() - started) * 1000.0
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=JEV_MODEL_VERSION,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response={"error": str(exc)},
                latency_ms=latency_ms,
                billed_units=0.0,
                error_status=status,
            )
        latency_ms = (time.perf_counter() - started) * 1000.0
        probability = _extract_probability(response, question)
        billed = float(response.usage.input_tokens or 0)
        return PredictionRecord(
            example_id=record.example_id,
            arm=self.arm,
            model_version=JEV_MODEL_VERSION,
            template_version=template_version,
            probability=probability,
            band=None,
            raw_response=_response_to_dict(response),
            latency_ms=latency_ms,
            billed_units=billed,
            error_status=None,
        )


def _jev_error_status(exc: Exception) -> str:
    message = str(exc).lower()
    if "max_tokens" in message or "context" in message:
        return MAX_TOKENS_ERROR
    return type(exc).__name__


def _template_version(question: QuestionSpec) -> str:
    return question.model_dump_json()


def _build_ts_questions(question: QuestionSpec) -> dict[str, Any]:
    built: dict[str, Any] = {}
    for qid, item in question.questions.items():
        if item.type == "noul":
            built[qid] = Noul(instructions=item.instructions)
        elif item.type == "choice":
            criteria = item.criteria or {}
            built[qid] = Choice(instructions=item.instructions, criteria=criteria)
        elif item.type == "score":
            built[qid] = Score(
                instructions=item.instructions, criteria=item.criteria or []
            )
        else:
            built[qid] = Noul(instructions=item.instructions)
    return built


def _first_question_id(question: QuestionSpec) -> str:
    return next(iter(question.questions.keys()))


def _extract_probability(response: object, question: QuestionSpec) -> float | None:
    qid = _first_question_id(question)
    answer = response.answers.get(qid)
    if answer is None:
        return None
    if hasattr(answer, "noul") and answer.noul is not None:
        return float(answer.noul)
    if hasattr(answer, "choice") and answer.choice is not None:
        return 1.0
    return None


def _response_to_dict(response: object) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    return {
        "model": getattr(response, "model", JEV_MODEL_VERSION),
        "answers": {
            key: _answer_to_dict(val) for key, val in response.answers.items()
        },
        "usage": {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        },
    }


def _answer_to_dict(answer: object) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": getattr(answer, "type", None)}
    if hasattr(answer, "noul"):
        payload["noul"] = getattr(answer, "noul", None)
    if hasattr(answer, "choice"):
        payload["choice"] = getattr(answer, "choice", None)
    return payload
