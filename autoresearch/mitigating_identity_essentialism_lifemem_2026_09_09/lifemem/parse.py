from __future__ import annotations

import re


def parse_option_code(raw: str, valid_codes: tuple[str, ...]) -> str | None:
    if not raw:
        return None
    text = raw.strip()
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
