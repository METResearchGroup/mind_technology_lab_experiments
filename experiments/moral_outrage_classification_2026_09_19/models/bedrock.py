"""Bedrock Converse engine for the five locked model IDs.

Run from the experiment folder:

    uv run python -c "from models.bedrock import BedrockEngine; print(BedrockEngine.__name__)"
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from shared.aws_region import AWS_REGION
from shared.brady_definition import BRADY_MORAL_OUTRAGE_INSTRUCTIONS
from shared.engine_loop import LabelTask, label_records
from shared.metrics import binary_label_from_probability
from shared.pricing import estimate_cost_usd
from shared.records import BEDROCK_MODEL_IDS, PredictionRecord
from shared.secrets import build_boto3_session
from shared.timer import timed

DEFAULT_BATCH_SIZE = 8
DEFAULT_MAX_LABEL_RETRIES = 3
STRUCTURED_OUTPUT_INSTRUCTIONS = (
    BRADY_MORAL_OUTRAGE_INSTRUCTIONS
    + ' Reply with JSON only: {"moral_outrage": true or false, '
    + '"probability": a number between 0 and 1}.'
)
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class BedrockEngine:
    """Score one post with a single Bedrock model id."""

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
        converse = self._converse if self._converse is not None else self._live_converse()
        try:
            response, latency_ms = _converse_once(converse, self.model_id, text)
        except Exception as exc:
            raise RuntimeError(
                f"Bedrock model {self.model_id} failed: {exc}"
            ) from exc
        moral_outrage, probability = _parse_converse_payload(response)
        binary_label = (
            binary_label_from_probability(probability)
            if probability is not None
            else int(moral_outrage)
        )
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        input_tokens = usage.get("inputTokens")
        output_tokens = usage.get("outputTokens")
        return PredictionRecord(
            source_row_id="",
            text=text,
            gold_label=0,
            model_name=self.model_name,
            probability=probability,
            binary_label=binary_label,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost_usd(
                self.model_name, input_tokens, output_tokens
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

    def _live_converse(self) -> Callable[..., object]:
        session = build_boto3_session()
        client = session.client("bedrock-runtime", region_name=AWS_REGION)
        return client.converse


@timed
def _converse_once(
    converse: Callable[..., object], model_id: str, text: str
) -> object:
    return converse(
        modelId=model_id,
        system=[{"text": STRUCTURED_OUTPUT_INSTRUCTIONS}],
        messages=[{"role": "user", "content": [{"text": text}]}],
    )


def _parse_converse_payload(
    response: object,
) -> tuple[bool, float | None]:
    text = _extract_text(response)
    payload = _parse_json_object(text)
    moral_outrage = bool(payload["moral_outrage"])
    if "probability" not in payload or payload["probability"] is None:
        return moral_outrage, None
    return moral_outrage, float(payload["probability"])


def _extract_text(response: object) -> str:
    if not isinstance(response, dict):
        raise ValueError("Bedrock response is not a mapping")
    content = response["output"]["message"]["content"]
    parts = [item.get("text", "") for item in content if isinstance(item, dict)]
    return "".join(parts)


def _parse_json_object(text: str) -> dict[str, object]:
    match = JSON_OBJECT_PATTERN.search(text)
    if match is None:
        raise ValueError("Bedrock response had no JSON object")
    return json.loads(match.group(0))
