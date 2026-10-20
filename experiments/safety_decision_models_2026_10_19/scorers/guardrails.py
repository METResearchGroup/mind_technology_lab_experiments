"""Bedrock Guardrails DecisionScorer (detect-only, filter action NONE).

Run from the experiment folder:

    uv run python -c "from scorers.guardrails import GuardrailsScorer; print(GuardrailsScorer.__name__)"
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from shared.records import ExampleRecord, PredictionRecord, QuestionSpec
from shared.secrets import AWS_REGION, build_boto3_session

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
STUDY_CONFIG = EXPERIMENT_ROOT / "configs" / "study.json"
GUARDRAILS_ARM = "guardrails"
TEXT_UNIT_CHARS = 1000
BAND_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
GuardrailStrength = Literal["low", "medium", "high"]


class GuardrailsScorer:
    """ApplyGuardrail with content filters only."""

    arm = GUARDRAILS_ARM

    def __init__(self, guardrail_id: str | None = None) -> None:
        config = _read_study_config()
        self._guardrail_id = guardrail_id or str(config.get("guardrail_id", "") or "")
        self._guardrail_version = str(config.get("guardrail_version", "") or "")
        self._crosswalk = config.get("crosswalk", {})
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
        model_version = self._guardrail_version or "bedrock-guardrails-detect"
        if not self._guardrail_id or not self._guardrail_version:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=model_version,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response={"error": "guardrail_id or guardrail_version not configured"},
                latency_ms=latency_ms,
                billed_units=_text_units(record.text),
                error_status="missing_guardrail_config",
            )
        try:
            response = self._client.apply_guardrail(
                guardrailIdentifier=self._guardrail_id,
                guardrailVersion=self._guardrail_version,
                source="INPUT",
                content=[{"text": {"text": record.text}}],
            )
            raw = dict(response)
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000.0
            return PredictionRecord(
                example_id=record.example_id,
                arm=self.arm,
                model_version=model_version,
                template_version=template_version,
                probability=None,
                band=None,
                raw_response={"error": str(exc)},
                latency_ms=latency_ms,
                billed_units=_text_units(record.text),
                error_status=type(exc).__name__,
            )
        latency_ms = (time.perf_counter() - started) * 1000.0
        filter_names = _crosswalk_filters_for_record(record, self._crosswalk)
        band = _band_for_filters(raw, filter_names)
        return PredictionRecord(
            example_id=record.example_id,
            arm=self.arm,
            model_version=model_version,
            template_version=template_version,
            probability=None,
            band=band,
            raw_response=raw,
            latency_ms=latency_ms,
            billed_units=_billed_units(raw, record.text),
            error_status=None,
        )


def band_blocks_at_strength(band: str, strength: GuardrailStrength) -> bool:
    """Map detect band plus strength to a block decision (RQ4 post-call rule)."""
    normalized = str(band).upper()
    if normalized == "NONE":
        return False
    rank = BAND_ORDER.get(normalized)
    if rank is None:
        return False
    threshold = {"low": 3, "medium": 2, "high": 1}[strength]
    return rank >= threshold


def _read_study_config() -> dict[str, Any]:
    if not STUDY_CONFIG.is_file():
        return {}
    payload = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


def _crosswalk_filters_for_record(
    record: ExampleRecord, crosswalk: dict[str, Any]
) -> list[str]:
    dataset_map = crosswalk.get(record.dataset, {})
    if not isinstance(dataset_map, dict):
        return []
    if isinstance(record.gold_labels, dict):
        names: list[str] = []
        for key, value in record.gold_labels.items():
            if not value:
                continue
            mapped = dataset_map.get(key, crosswalk.get("default", []))
            if isinstance(mapped, list):
                names.extend(str(name) for name in mapped)
        return _unique_preserve(names)
    if isinstance(record.gold_labels, str):
        mapped = dataset_map.get(record.gold_labels, crosswalk.get("default", []))
        if isinstance(mapped, list):
            return [str(name) for name in mapped]
    default = crosswalk.get("default", [])
    return [str(name) for name in default] if isinstance(default, list) else []


def _unique_preserve(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def _band_for_filters(raw: dict[str, Any], filter_names: list[str]) -> str:
    by_type = _filter_bands(raw)
    if filter_names:
        relevant = [by_type[name] for name in filter_names if name in by_type]
        if relevant:
            return _max_band(relevant)
        return "NONE"
    if by_type:
        return _max_band(by_type.values())
    return "NONE"


def _filter_bands(raw: dict[str, Any]) -> dict[str, str]:
    bands: dict[str, str] = {}
    for assessment in raw.get("assessments", []):
        filters = assessment.get("contentPolicy", {}).get("filters", [])
        for filt in filters:
            filter_type = str(filt.get("type", "")).upper()
            if not filter_type:
                continue
            confidence = str(filt.get("confidence", "NONE")).upper()
            if confidence not in BAND_ORDER:
                confidence = "NONE"
            prior = bands.get(filter_type, "NONE")
            bands[filter_type] = _max_band([prior, confidence])
    return bands


def _max_band(bands: list[str]) -> str:
    best = "NONE"
    for band in bands:
        normalized = str(band).upper()
        if normalized in BAND_ORDER and BAND_ORDER[normalized] > BAND_ORDER[best]:
            best = normalized
    return best


def _text_units(text: str) -> float:
    length = len(text)
    if length == 0:
        return 0.0
    return float((length + TEXT_UNIT_CHARS - 1) // TEXT_UNIT_CHARS)


def _billed_units(raw: dict[str, Any], text: str) -> float:
    usage = raw.get("usage", {})
    if isinstance(usage, dict):
        units = usage.get("contentPolicyUnits")
        if units is not None:
            return float(units)
    return _text_units(text)
