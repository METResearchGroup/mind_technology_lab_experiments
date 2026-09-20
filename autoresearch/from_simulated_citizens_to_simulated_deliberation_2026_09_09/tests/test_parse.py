from __future__ import annotations

from parse import match_position, parse_choice, parse_public
from questions import QUESTION_BY_ID


def test_parse_choice_korean_json() -> None:
    question = QUESTION_BY_ID["env_priority"]
    text = '{"choice": "환경 보호를 우선한다 (경제성장이 다소 둔화되더라도)"}'
    assert parse_choice(text, question.position_a, question.position_b) == "A"


def test_parse_choice_wrapped_markdown() -> None:
    question = QUESTION_BY_ID["clim_tech"]
    text = '```json\n{"choice": "순환경제 기술 (재활용과 폐기물 관리)"}\n```'
    assert parse_choice(text, question.position_a, question.position_b) == "B"


def test_parse_choice_uses_position_keys_when_order_is_ba() -> None:
    question = QUESTION_BY_ID["clim_strategy"]
    text = '{"choice": "에너지 전환을 우선한다 (재생에너지 확대)"}'
    assert parse_choice(text, question.position_b, question.position_a) == "B"


def test_letter_maps_to_displayed_option() -> None:
    question = QUESTION_BY_ID["housing"]
    assert match_position("A", question.position_b, question.position_a) == "B"
    assert match_position("A", question.position_a, question.position_b) == "A"
    assert match_position("B", question.position_a, question.position_b) == "B"


def test_parse_public_json() -> None:
    assert parse_public('{"public": "재생에너지에 투자해야 합니다."}') == (
        "재생에너지에 투자해야 합니다."
    )
