"""Bedrock Guardrails DecisionScorer (detect-only, filter action NONE).

Run from the experiment folder:

    uv run python -c "from scorers.guardrails import GuardrailsScorer; print(GuardrailsScorer.__name__)"
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from shared.records import ExampleRecord, PredictionRecord, QuestionSpec
from shared.secrets import AWS_REGION, build_boto3_session

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
STUDY_CONFIG = EXPERIMENT_ROOT / "configs" / "study.json"
GUARDRAILS_ARM = "guardrails"
GUARDRAILS_MODEL_VERSION = "bedrock-guardrails-detect"
TEXT_UNIT_CHARS = 1000


class GuardrailsScorer:
    """ApplyGuardrail with content filters only."""

    arm = GUARDRAILS_ARM

    def __init__(self, guardrail_id: str | None = None) -> None:
        self._guardrail_id = guardrail_id or _read_guardrail_id()
        session = build_boto3_session()
        self._client = session.client("bedrock-runtime", region_name=AWS_REGION)

    def score(
        self, records: list[ExampleRecord], question: QuestionSpec
    ) -> list[PredictionRecord]:
        """Score each record with one detect-only guardrail call."""
        return [self._score_one(record, question) for record in records]

    def _score_one(
        self, record: ExampleRecord, question: QuestionSpec
    ) -> PredictionRecord:
        started = time.perf_counter()
        template_version = question.model_dump_json()
        if not self._guardrail_id:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=GUARDRAILS_MODEL_VERSION,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response={"error": "guardrail_id not configured"},
                latency_ms=latency_ms,
                billed_units=_text_units(record.text),
                error_status="missing_guardrail_id",
            )
        try:
            response = self._client.apply_guardrail(
                guardrailIdentifier=self._guardrail_id,
                guardrailVersion="DRAFT",
                source="INPUT",
                content=[{"text": {"text": record.text}}],
            )
            raw = dict(response)
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000.0
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=GUARDRAILS_MODEL_VERSION,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response={"error": str(exc)},
                latency_ms=latency_ms,
                billed_units=_text_units(record.text),
                error_status=type(exc).__name__,
            )
        latency_ms = (time.perf_counter() - started) * 1000.0
        band = _max_content_filter_band(raw)
        return PredictionRecord(
            example_id=record.example_id,
            arm=self.arm,
            model_version=GUARDRAILS_MODEL_VERSION,
            template_version=template_version,
            probability=None,
            band=band,
            raw_response=raw,
            latency_ms=latency_ms,
            billed_units=_text_units(record.text),
            error_status=None,
        )


def _read_guardrail_id() -> str:
    if not STUDY_CONFIG.is_file():
        return ""
    payload = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    return str(payload.get("guardrail_id", "") or "")


def _text_units(text: str) -> float:
    length = len(text)
    if length == 0:
        return 0.0
    return float((length + TEXT_UNIT_CHARS - 1) // TEXT_UNIT_CHARS)


def _max_content_filter_band(raw: dict[str, Any]) -> str:
    assessments = raw.get("assessments", [])
    order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    best = "NONE"
    for assessment in assessments:
        filters = assessment.get("contentPolicy", {}).get("filters", [])
        for filt in filters:
            band = str(filt.get("confidence", filt.get("type", "NONE"))).upper()
            if band in order and order[band] > order[best]:
                best = band
    return best
