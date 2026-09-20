"""Prompt templates translated from Appendix H of arXiv:2609.07573.

The original experiments were run in Korean. These templates keep that
language for model calls and expose English copies for the dashboard.
"""

from __future__ import annotations

from questions import Position, Question

SYSTEM_KO = (
    "당신은 아래 프로필을 가진 대한민국 시민입니다.\n"
    "[프로필] {profile}\n"
    "[배경] {narrative}\n"
    "지정된 JSON 형식으로만 답하십시오."
)

SYSTEM_KO_CITIZEN = "당신은 대한민국 시민입니다.\n지정된 JSON 형식으로만 답하십시오."

SYSTEM_KO_NONE = "지정된 JSON 형식으로만 답하십시오."

SURVEY_KO = (
    "[쟁점] {topic}\n"
    "{transcript_block}"
    "아래 두 입장 중 어느 쪽에 더 가깝습니까?\n"
    "반드시 하나를 고르십시오.\n\n"
    "- {first}\n"
    "- {second}\n\n"
    "JSON으로만 답하고, 입장 문구를 그대로 복사하십시오:\n"
    '{{"choice": "..."}}'
)

SPEECH_KO = (
    "[쟁점] {topic}\n"
    "[입장] {first} 또는 {second}\n"
    "{side_line}"
    "[지금까지의 토론]\n"
    "{transcript}\n\n"
    "당신은 {name}입니다. 위 토론을 이어서 2-4문장으로 자신의 견해를 "
    "말하십시오. 발화만 JSON으로 답하십시오:\n"
    '{{"public": "..."}}'
)

OPENING_KO = (
    "[쟁점] {topic}\n"
    "[입장] {first} 또는 {second}\n"
    '[당신의 입장] 당신은 "{side}" 쪽입니다.\n'
    "당신은 {name}입니다. 이 입장을 지지하는 이유를 2-4문장으로 "
    "말하십시오. 발화만 JSON으로 답하십시오:\n"
    '{{"public": "..."}}'
)


def profile_line(
    *,
    age: int,
    sex_ko: str,
    region_ko: str,
    education_ko: str,
    occupation: str,
    household: str,
) -> str:
    return (
        f"{age}세 {sex_ko}, {region_ko}, 학력 {education_ko}, "
        f"직업 {occupation}, {household}"
    )


def survey_user(
    question: Question,
    first: Position,
    second: Position,
    transcript: str | None,
) -> str:
    if transcript:
        block = f"[지금까지의 토론]\n{transcript}\n\n"
    else:
        block = ""
    return SURVEY_KO.format(
        topic=question.topic_ko,
        transcript_block=block,
        first=first.ko,
        second=second.ko,
    )


def speech_user(
    question: Question,
    first: Position,
    second: Position,
    name: str,
    transcript: str,
    side: str | None = None,
) -> str:
    side_line = f'[당신의 입장] 당신은 "{side}"를 지지합니다.\n' if side else ""
    empty = "아직 아무도 발언하지 않았습니다."
    shown = transcript.strip() if transcript.strip() else empty
    return SPEECH_KO.format(
        topic=question.topic_ko,
        first=first.ko,
        second=second.ko,
        side_line=side_line,
        transcript=shown,
        name=name,
    )


def opening_user(
    question: Question,
    first: Position,
    second: Position,
    name: str,
    side: str,
) -> str:
    return OPENING_KO.format(
        topic=question.topic_ko,
        first=first.ko,
        second=second.ko,
        side=side,
        name=name,
    )
