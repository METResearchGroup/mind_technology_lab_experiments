from __future__ import annotations

import re

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Drop Qwen thinking spans before Likert parsing."""
    if not text:
        return ""
    cleaned = _THINK_BLOCK.sub("", text)
    marker = "</think>"
    lower = cleaned.lower()
    if marker in lower:
        cleaned = cleaned[lower.rfind(marker) + len(marker) :]
    return cleaned.strip()


def parse_option_code(raw: str, valid_codes: tuple[str, ...]) -> str | None:
    if not raw:
        return None
    text = strip_thinking(raw)
    if text in valid_codes:
        return text
    match = re.search(r"\d+", text)
    if match and match.group(0) in valid_codes:
        return match.group(0)
    lowered = text.lower()
    for code in valid_codes:
        if code.lower() == lowered:
            return code
    return None
