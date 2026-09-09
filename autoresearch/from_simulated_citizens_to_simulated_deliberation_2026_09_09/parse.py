"""Parse forced-choice JSON and public speech JSON from model output."""

from __future__ import annotations

import json
import re

from questions import Position

JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: str) -> dict[str, object] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned)
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        loaded = json.loads(cleaned)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        pass
    match = JSON_RE.search(cleaned)
    if not match:
        return None
    try:
        loaded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if isinstance(loaded, dict):
        return loaded
    return None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def match_position(choice: str, first: Position, second: Position) -> str | None:
    raw = choice.strip()
    if not raw:
        return None
    if raw in {"A", "1", "Position A", "입장 A"}:
        return first.key
    if raw in {"B", "2", "Position B", "입장 B"}:
        return second.key
    candidates = (
        (first.ko, first.key),
        (first.en, first.key),
        (second.ko, second.key),
        (second.en, second.key),
    )
    normalized = _normalize(raw)
    for label, key in candidates:
        if _normalize(label) == normalized:
            return key
    for label, key in candidates:
        if _normalize(label) in normalized or normalized in _normalize(label):
            return key
    return None


def parse_choice(text: str, first: Position, second: Position) -> str | None:
    payload = extract_json_object(text)
    if payload and "choice" in payload:
        return match_position(str(payload["choice"]), first, second)
    return match_position(text, first, second)


def parse_public(text: str) -> str:
    payload = extract_json_object(text)
    if payload and "public" in payload:
        return str(payload["public"]).strip()
    return text.strip()
