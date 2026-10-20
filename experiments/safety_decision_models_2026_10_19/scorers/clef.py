"""Clef and Clef-flash DecisionScorer via Cloudflare Workers AI.

Run from the experiment folder:

    uv run python -c "from scorers.clef import ClefScorer; print(ClefScorer.__name__)"
"""

from __future__ import annotations

import time
from typing import Any

import requests

from shared.cache import estimate_token_count
from shared.records import ExampleRecord, PredictionRecord, QuestionSpec
from shared.secrets import load_cloudflare_workers_ai

CLEF_MODEL_ID = "@cf/cloudflare/clef"
CLEF_FLASH_MODEL_ID = "@cf/cloudflare/clef-flash"
CLEF_TOKEN_LIMIT = 64000
CLEF_FLASH_TOKEN_LIMIT = 24576
TRUNCATED_STATUS = "truncated"
WORKERS_AI_TIMEOUT_SECONDS = 120.0


class ClefScorer:
    """Score rows with Clef or Clef-flash on Workers AI."""

    def __init__(self, arm: str, api_token: str | None = None) -> None:
        if arm not in ("clef", "clef-flash"):
            raise ValueError(f"Unsupported Clef arm: {arm}")
        self.arm = arm
        self._model_field = "clef-flash" if arm == "clef-flash" else "clef"
        self._hosted_model = (
            CLEF_FLASH_MODEL_ID if arm == "clef-flash" else CLEF_MODEL_ID
        )
        self._token_limit = (
            CLEF_FLASH_TOKEN_LIMIT if arm == "clef-flash" else CLEF_TOKEN_LIMIT
        )
        account_id, token = load_cloudflare_workers_ai()
        self._account_id = account_id
        self._api_token = api_token or token

    def score(
        self, records: list[ExampleRecord], question: QuestionSpec
    ) -> list[PredictionRecord]:
        """Score each record."""
        return [self._score_one(record, question) for record in records]

    def _score_one(
        self, record: ExampleRecord, question: QuestionSpec
    ) -> PredictionRecord:
        started = time.perf_counter()
        template_version = question.model_dump_json()
        pre_truncated = estimate_token_count(record.text) > self._token_limit
        body = _build_clef_body(record.text, question, self._model_field)
        url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self._account_id}"
            f"/ai/run/{self._hosted_model}"
        )
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {self._api_token}"},
                json=body,
                timeout=WORKERS_AI_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=self._hosted_model,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response={"error": str(exc)},
                latency_ms=latency_ms,
                billed_units=0.0,
                error_status=type(exc).__name__,
            )
        latency_ms = (time.perf_counter() - started) * 1000.0
        result = payload.get("result", payload)
        billed = float(_usage_input_tokens(result))
        truncated = pre_truncated or billed > self._token_limit
        probability = _extract_probability(result, question)
        return PredictionRecord(
            example_id=record.example_id,
            arm=self.arm,
            model_version=self._hosted_model,
            template_version=template_version,
            probability=probability,
            band=None,
            raw_response=result if isinstance(result, dict) else {"result": result},
            latency_ms=latency_ms,
            billed_units=billed,
            error_status=TRUNCATED_STATUS if truncated else None,
        )


def _build_clef_body(
    text: str, question: QuestionSpec, model_field: str
) -> dict[str, Any]:
    questions: dict[str, Any] = {}
    for qid, item in question.questions.items():
        questions[qid] = {
            "type": item.type,
            "instructions": item.instructions,
            "criteria": item.criteria,
        }
    return {"model": model_field, "state": text, "questions": questions}


def _usage_input_tokens(result: dict[str, Any]) -> int:
    usage = result.get("usage", {})
    return int(usage.get("input_tokens", 0))


def _first_question_id(question: QuestionSpec) -> str:
    return next(iter(question.questions.keys()))


def _extract_probability(result: dict[str, Any], question: QuestionSpec) -> float | None:
    qid = _first_question_id(question)
    answers = result.get("answers", {})
    answer = answers.get(qid, {})
    if answer.get("type") == "noul":
        value = answer.get("noul")
        return float(value) if value is not None else None
    if answer.get("type") == "choice":
        return 1.0
    return None
