"""Pre-deliberation forced-choice survey (temperature 0)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from client import ChatClient
from parse import parse_choice
from personas import Persona
from prompts import (
    SYSTEM_KO,
    SYSTEM_KO_CITIZEN,
    SYSTEM_KO_NONE,
    profile_line,
    survey_user,
)
from questions import Position, Question


@dataclass(frozen=True)
class SurveyRecord:
    persona_id: str | None
    question_id: str
    condition: str
    order: str
    choice: str | None
    raw: str
    first_key: str


def ordered_positions(
    question: Question, persona_id: str
) -> tuple[str, Position, Position]:
    digest = hashlib.sha256(f"{persona_id}:{question.id}".encode()).hexdigest()
    if int(digest, 16) % 2 == 0:
        return "AB", question.position_a, question.position_b
    return "BA", question.position_b, question.position_a


def positions_for_order(question: Question, order: str) -> tuple[Position, Position]:
    if order == "BA":
        return question.position_b, question.position_a
    return question.position_a, question.position_b


def choice_from_raw(raw: str, question: Question, order: str) -> str | None:
    first, second = positions_for_order(question, order)
    return parse_choice(raw, first, second)


def system_for_persona(persona: Persona | None, condition: str) -> str:
    if condition == "none" or persona is None:
        return SYSTEM_KO_NONE
    if condition == "citizen":
        return SYSTEM_KO_CITIZEN
    if persona is None:
        raise ValueError("persona is required for this condition")
    if condition == "demographics":
        profile = profile_line(
            age=persona.age,
            sex_ko=persona.sex_ko,
            region_ko=persona.region_ko,
            education_ko=persona.education_ko,
            occupation="정보 없음",
            household="정보 없음",
        )
        narrative = "추가 서사 없음."
    else:
        profile = profile_line(
            age=persona.age,
            sex_ko=persona.sex_ko,
            region_ko=persona.region_ko,
            education_ko=persona.education_ko,
            occupation=persona.occupation,
            household=persona.household,
        )
        narrative = persona.narrative
    return SYSTEM_KO.format(profile=profile, narrative=narrative)


def run_survey_item(
    client: ChatClient,
    question: Question,
    *,
    persona: Persona | None,
    condition: str,
    transcript: str | None = None,
    temperature: float = 0.0,
    seed: int | None = None,
) -> SurveyRecord:
    persona_id = persona.id if persona else f"{condition}:{question.id}"
    order, first, second = ordered_positions(question, persona_id)
    messages = [
        {"role": "system", "content": system_for_persona(persona, condition)},
        {"role": "user", "content": survey_user(question, first, second, transcript)},
    ]
    result = client.chat(
        messages,
        temperature=temperature,
        max_tokens=96,
        seed=seed,
    )
    choice = parse_choice(result.text, first, second)
    return SurveyRecord(
        persona_id=persona.id if persona else None,
        question_id=question.id,
        condition=condition,
        order=order,
        choice=choice,
        raw=result.text,
        first_key=first.key,
    )
