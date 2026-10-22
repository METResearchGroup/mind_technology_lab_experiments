"""Clef and Clef-flash DecisionScorer via Cloudflare Workers AI.

Run from the experiment folder:

    uv run python -c "from scorers.clef import ClefScorer; print(ClefScorer.__name__)"
"""

from __future__ import annotations

import json
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
ERROR_BODY_MAX_CHARS = 8000
PRIMARY_HEAD_ORDER = (
    "toxic",
    "answer",
    "harm",
    "harmful",
    "refuse",
    "prompt_harm",
)


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
        if response.status_code >= 400:
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=self._hosted_model,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response=_http_error_raw_response(response),
                latency_ms=latency_ms,
                billed_units=0.0,
                error_status=f"HTTP{response.status_code}",
            )
        try:
            payload = response.json()
        except ValueError:
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=self._hosted_model,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response={
                    "status_code": response.status_code,
                    "body": response.text[:ERROR_BODY_MAX_CHARS],
                },
                latency_ms=latency_ms,
                billed_units=0.0,
                error_status="InvalidJSON",
            )
        result = payload.get("result", payload)
        if not isinstance(result, dict):
            result = {"result": result}
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
            raw_response=result,
            latency_ms=latency_ms,
            billed_units=billed,
            error_status=TRUNCATED_STATUS if truncated else None,
        )


def _build_clef_body(
    text: str, question: QuestionSpec, model_field: str
) -> dict[str, Any]:
    questions: dict[str, Any] = {}
    for qid, item in question.questions.items():
        entry: dict[str, Any] = {
            "type": item.type,
            "instructions": _format_instructions(item.instructions),
        }
        if item.criteria is not None:
            entry["criteria"] = item.criteria
        questions[qid] = entry
    return {"model": model_field, "state": text, "questions": questions}


def _format_instructions(instructions: Any) -> Any:
    if isinstance(instructions, str):
        return instructions
    if not isinstance(instructions, dict):
        return instructions
    question = instructions.get("question")
    if not isinstance(question, str):
        return instructions
    category = instructions.get("category")
    if not isinstance(category, dict):
        return question
    name = category.get("name")
    definition = category.get("definition")
    parts: list[str] = []
    if isinstance(name, str) and name:
        parts.append(f"Category: {name}.")
    if isinstance(definition, str) and definition:
        parts.append(definition)
    if parts:
        return f"{' '.join(parts)} {question}"
    return question


def _http_error_raw_response(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {
            "status_code": response.status_code,
            "body": response.text[:ERROR_BODY_MAX_CHARS],
        }
    serialized = json.dumps(data)
    if len(serialized) > ERROR_BODY_MAX_CHARS:
        errors = data.get("errors") if isinstance(data, dict) else None
        return {
            "status_code": response.status_code,
            "errors": errors,
            "truncated": True,
        }
    if isinstance(data, dict):
        return {"status_code": response.status_code, **data}
    return {"status_code": response.status_code, "body": data}


def _usage_input_tokens(result: dict[str, Any]) -> int:
    usage = result.get("usage", {})
    return int(usage.get("input_tokens", 0))


def _primary_question_id(question: QuestionSpec) -> str:
    for head_id in PRIMARY_HEAD_ORDER:
        if head_id in question.questions:
            return head_id
    return next(iter(question.questions.keys()))


def _probability_from_answer(answer: Any) -> float | None:
    if not isinstance(answer, dict):
        return None
    answer_type = answer.get("type")
    if answer_type == "noul":
        value = answer.get("noul")
        return float(value) if value is not None else None
    if answer_type == "score":
        value = answer.get("score")
        if value is not None:
            return float(value)
        return None
    if answer_type == "choice":
        choice = answer.get("choice")
        probabilities = answer.get("probabilities")
        if (
            choice is not None
            and isinstance(probabilities, dict)
            and choice in probabilities
            and probabilities[choice] is not None
        ):
            return float(probabilities[choice])
        confidence = answer.get("confidence")
        if confidence is not None:
            return float(confidence)
        return 1.0 if choice is not None else None
    return None


def _extract_probability(result: dict[str, Any], question: QuestionSpec) -> float | None:
    answers = result.get("answers", {})
    if not isinstance(answers, dict):
        return None
    qid = _primary_question_id(question)
    return _probability_from_answer(answers.get(qid))
