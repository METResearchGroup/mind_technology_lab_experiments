"""Bedrock Converse engine copied from mirrorView-task bedrock_engine.py.

The public experiment class stays ``BedrockEngine``. The Converse helper,
Pydantic parse, inner retry, and content-filter handling come from
https://github.com/METResearchGroup/mirrorView-task/blob/main/data_platform/generate_features/engines/bedrock_engine.py

Run from the experiment folder:

    uv run python -c "from models.bedrock import BedrockEngine; print(BedrockEngine.__name__)"
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, ValidationError

from shared.aws_region import AWS_REGION
from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS
from shared.engine_loop import LabelTask, http_status_code, label_records
from shared.metrics import binary_label_from_probability
from shared.pricing import estimate_cost_usd
from shared.records import BEDROCK_MODEL_IDS, PredictionRecord
from shared.secrets import build_boto3_session
from shared.timer import timed

DEFAULT_BATCH_SIZE = 8
DEFAULT_MAX_LABEL_RETRIES = 3
BEDROCK_MAX_TOKENS = 32
BEDROCK_FALLBACK_MAX_TOKENS = 1024
BEDROCK_TEMPERATURE = 0.0
JSON_INSTRUCTION_PREFIX = (
    "Reply with a single JSON object only. The object must have these fields: "
)
JSON_FENCE = "```"
JSON_FENCE_LANGUAGE = "json"
CONVERSE_RETRY_ATTEMPTS = 8
CONVERSE_RETRY_SLEEP_SECONDS = 1.0
CONTENT_FILTER_MARKER = "blocked by our content filters"
CONTENT_FILTER_STOP_REASONS = frozenset({"content_filtered", "guardrail_intervened"})
RETRYABLE_CONVERSE_ERRORS = (
    json.JSONDecodeError,
    ValueError,
    ValidationError,
    ClientError,
)


class BedrockRuntimeClient(Protocol):
    """Subset of the Bedrock Runtime client used by the Converse engine."""

    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


class BedrockContentFilterError(Exception):
    """Bedrock refused the prompt under its content filters."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BedrockProviderError(RuntimeError):
    """Converse failed. status_code is set for HTTP-shaped errors."""

    def __init__(self, message: str, status_code: int | None) -> None:
        super().__init__(message)
        self.status_code = status_code


class MoralOutrageLabel(BaseModel):
    """Structured yes/no label returned by one Bedrock Converse call."""

    moral_outrage: bool
    probability: float | None = Field(default=None, ge=0.0, le=1.0)


@dataclass(frozen=True)
class BedrockUsage:
    """Token counts from one Converse call."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


class _CallableConverseClient:
    """Adapt a bare converse callable to the client protocol."""

    def __init__(self, converse: Callable[..., object]) -> None:
        self._converse = converse

    def converse(self, **kwargs: Any) -> dict[str, Any]:
        return self._converse(**kwargs)  # type: ignore[return-value]


class BedrockEngine:
    """Score one post with a single locked Bedrock model id."""

    def __init__(
        self, model_id: str, converse: Callable[..., object] | None = None
    ) -> None:
        if model_id not in BEDROCK_MODEL_IDS:
            raise ValueError(f"Unsupported Bedrock model id: {model_id}")
        self.model_id = model_id
        self.model_name = f"Bedrock:{model_id}"
        self._converse = converse

    def label_one(self, text: str) -> PredictionRecord:
        """Score one post text with Converse."""
        client = self._client()
        try:
            (parsed, usage), latency_ms = _timed_converse_label(client, self.model_id, text)
        except BedrockContentFilterError:
            raise
        except Exception as exc:
            raise BedrockProviderError(
                f"Bedrock model {self.model_id} failed: {exc}",
                http_status_code(exc),
            ) from exc
        probability = parsed.probability
        binary_label = (
            binary_label_from_probability(probability)
            if probability is not None
            else int(parsed.moral_outrage)
        )
        return PredictionRecord(
            source_row_id="",
            text=text,
            gold_label=0,
            model_name=self.model_name,
            probability=probability,
            binary_label=binary_label,
            latency_ms=latency_ms,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            estimated_cost_usd=estimate_cost_usd(
                self.model_name, usage.input_tokens, usage.output_tokens
            ),
        )

    def label_records(
        self, tasks: list[LabelTask], output_dir: object
    ) -> list[PredictionRecord]:
        """Score tasks through the shared skip-seen loop."""
        return label_records(
            tasks,
            self._label_task,
            Path(str(output_dir)),
            DEFAULT_BATCH_SIZE,
            DEFAULT_MAX_LABEL_RETRIES,
        )

    def _label_task(self, task: LabelTask) -> PredictionRecord:
        record = self.label_one(task.text)
        return record.model_copy(
            update={
                "source_row_id": task.source_row_id,
                "text": task.text,
                "gold_label": task.gold_label,
            }
        )

    def _client(self) -> BedrockRuntimeClient:
        if self._converse is not None:
            return _CallableConverseClient(self._converse)
        session = build_boto3_session()
        return session.client("bedrock-runtime", region_name=AWS_REGION)


def json_instruction_for_schema(output_schema: type[BaseModel]) -> str:
    """Return a JSON-only instruction derived from schema field names and types."""
    schema = output_schema.model_json_schema()
    properties = schema.get("properties") or {}
    required = schema.get("required") or list(properties)
    phrases = [_schema_field_phrase(name, properties.get(name) or {}) for name in required]
    return f"{JSON_INSTRUCTION_PREFIX}{'; '.join(phrases)}."


def _schema_field_phrase(name: str, field: dict[str, Any]) -> str:
    type_name = str(field.get("type", "value"))
    enum_values = field.get("enum")
    if not enum_values:
        return f"{name} ({type_name})"
    allowed = ", ".join(str(value) for value in enum_values)
    return f"{name} ({type_name}: {allowed})"


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model text, ignoring optional markdown fences."""
    stripped = text.strip()
    if _is_content_filter_text(stripped):
        raise BedrockContentFilterError(stripped)
    if stripped.startswith(JSON_FENCE):
        stripped = _strip_markdown_fence(stripped)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as error:
        payload = _payload_from_braces(stripped)
        if payload is None:
            raise ValueError(f"Bedrock response was not JSON: {stripped!r}") from error
    if not isinstance(payload, dict):
        raise ValueError("Bedrock response JSON must be an object")
    return payload


def _is_content_filter_text(text: str) -> bool:
    return CONTENT_FILTER_MARKER in text.lower()


def _payload_from_braces(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _strip_markdown_fence(text: str) -> str:
    body = text.strip().removeprefix(JSON_FENCE).strip()
    if body.lower().startswith(JSON_FENCE_LANGUAGE):
        body = body[len(JSON_FENCE_LANGUAGE) :].strip()
    if body.endswith(JSON_FENCE):
        body = body[: -len(JSON_FENCE)].strip()
    return body


def converse_label(
    client: BedrockRuntimeClient,
    model_id: str,
    system_prompt: str,
    output_schema: type[BaseModel],
    user_text: str,
    max_tokens: int = BEDROCK_MAX_TOKENS,
) -> tuple[BaseModel, BedrockUsage]:
    """Return structured output and token usage from one Converse call."""
    last_error: Exception | None = None
    for attempt in range(CONVERSE_RETRY_ATTEMPTS):
        try:
            return _converse_once(
                client,
                model_id,
                system_prompt,
                output_schema,
                user_text,
                max_tokens,
            )
        except RETRYABLE_CONVERSE_ERRORS as error:
            last_error = error
            print(
                f"Bedrock Converse retry {attempt + 1}/{CONVERSE_RETRY_ATTEMPTS}: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            if attempt + 1 >= CONVERSE_RETRY_ATTEMPTS:
                break
            time.sleep(CONVERSE_RETRY_SLEEP_SECONDS)
    if last_error is None:
        raise RuntimeError("Converse retry loop exited without a result")
    raise last_error


def _converse_once(
    client: BedrockRuntimeClient,
    model_id: str,
    system_prompt: str,
    output_schema: type[BaseModel],
    user_text: str,
    max_tokens: int = BEDROCK_MAX_TOKENS,
) -> tuple[BaseModel, BedrockUsage]:
    inference_config: dict[str, float | int] = {
        "maxTokens": max_tokens,
        "temperature": BEDROCK_TEMPERATURE,
    }
    try:
        response = _invoke_converse(
            client, model_id, system_prompt, output_schema, user_text, inference_config
        )
    except ClientError as error:
        if not _is_unsupported_temperature(error):
            raise
        inference_config = {"maxTokens": max_tokens}
        response = _invoke_converse(
            client, model_id, system_prompt, output_schema, user_text, inference_config
        )
    try:
        text = _first_text_block(response)
        parsed = output_schema.model_validate(parse_json_object(text))
    except (ValueError, json.JSONDecodeError, ValidationError):
        if (
            str(response.get("stopReason", "")) == "max_tokens"
            and max_tokens < BEDROCK_FALLBACK_MAX_TOKENS
        ):
            return _converse_once(
                client,
                model_id,
                system_prompt,
                output_schema,
                user_text,
                BEDROCK_FALLBACK_MAX_TOKENS,
            )
        raise
    return parsed, _usage_from_response(response)


def _invoke_converse(
    client: BedrockRuntimeClient,
    model_id: str,
    system_prompt: str,
    output_schema: type[BaseModel],
    user_text: str,
    inference_config: dict[str, float | int],
) -> dict[str, Any]:
    return client.converse(
        modelId=model_id,
        system=[{"text": f"{system_prompt}\n{json_instruction_for_schema(output_schema)}"}],
        messages=[{"role": "user", "content": [{"text": user_text}]}],
        inferenceConfig=inference_config,
    )


def _is_unsupported_temperature(error: ClientError) -> bool:
    message = str(error).lower()
    mentions_temperature = "temperature" in message
    unsupported = "doesn't support" in message or "does not support" in message
    deprecated = "deprecated" in message
    return mentions_temperature and (unsupported or deprecated)


@timed
def _timed_converse_label(
    client: BedrockRuntimeClient, model_id: str, text: str
) -> tuple[MoralOutrageLabel, BedrockUsage]:
    parsed, usage = converse_label(
        client,
        model_id,
        BRADY_MORAL_OUTRAGE_INSTRUCTIONS,
        MoralOutrageLabel,
        text,
    )
    if not isinstance(parsed, MoralOutrageLabel):
        raise TypeError(f"Expected MoralOutrageLabel, got {type(parsed)}")
    return parsed, usage


def _first_text_block(response: dict[str, Any]) -> str:
    content = response["output"]["message"]["content"]
    stop_reason = str(response.get("stopReason", ""))
    for block in content:
        text = block.get("text")
        if text:
            return _text_or_content_filter(str(text), stop_reason)
    if stop_reason in CONTENT_FILTER_STOP_REASONS:
        raise BedrockContentFilterError(f"stopReason={stop_reason!r}")
    raise ValueError(
        "Bedrock Converse response had no text "
        f"(stopReason={stop_reason!r}, content={content!r})"
    )


def _text_or_content_filter(text: str, stop_reason: str) -> str:
    if stop_reason in CONTENT_FILTER_STOP_REASONS or _is_content_filter_text(text):
        raise BedrockContentFilterError(text)
    return text


def _usage_from_response(response: dict[str, Any]) -> BedrockUsage:
    usage = response.get("usage", {})
    input_tokens = int(usage.get("inputTokens", 0))
    output_tokens = int(usage.get("outputTokens", 0))
    return BedrockUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )
