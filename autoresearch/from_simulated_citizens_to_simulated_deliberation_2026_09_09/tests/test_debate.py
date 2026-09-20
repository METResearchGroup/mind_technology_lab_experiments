from __future__ import annotations

from debate import Turn, format_transcript


def test_monologue_hides_other_speakers() -> None:
    turns = [
        Turn(1, "a", "민지", "첫번째", ["a"]),
        Turn(1, "b", "서준", "두번째", ["b"]),
    ]
    text = format_transcript(turns, "a")
    assert "민지" in text
    assert "서준" not in text


def test_debate_shows_full_log() -> None:
    turns = [
        Turn(1, "a", "민지", "첫번째", ["a", "b"]),
        Turn(1, "b", "서준", "두번째", ["a", "b"]),
    ]
    text = format_transcript(turns, None)
    assert "민지" in text
    assert "서준" in text
