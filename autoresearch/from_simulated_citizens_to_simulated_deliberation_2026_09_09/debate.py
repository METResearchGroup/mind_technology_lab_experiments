"""Six-agent, three-round deliberation and sealed-monologue controls."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from client import ChatClient
from parse import parse_public
from personas import Persona
from prompts import opening_user, speech_user
from questions import Question
from survey import SurveyRecord, run_survey_item, system_for_persona


@dataclass
class Turn:
    round_index: int
    speaker_id: str
    speaker_name: str
    text: str
    visible_to: list[str]


@dataclass
class AgentState:
    persona: Persona
    assigned_side: str
    stances: list[str | None] = field(default_factory=list)


@dataclass
class RoomResult:
    room_id: str
    question_id: str
    protocol: str
    start_composition: str
    agents: list[AgentState]
    turns: list[Turn]
    a_counts: list[int]


def format_transcript(turns: list[Turn], viewer_id: str | None) -> str:
    lines: list[str] = []
    for turn in turns:
        if viewer_id is not None and viewer_id not in turn.visible_to:
            continue
        lines.append(f"{turn.speaker_name}: {turn.text}")
    return "\n".join(lines)


def pick_balanced_agents(
    question_id: str,
    personas: list[Persona],
    choices: dict[str, str],
    rng: random.Random,
) -> list[tuple[Persona, str]] | None:
    a_pool = [p for p in personas if choices.get(p.id) == "A"]
    b_pool = [p for p in personas if choices.get(p.id) == "B"]
    if len(a_pool) < 3 or len(b_pool) < 3:
        return None
    rng.shuffle(a_pool)
    rng.shuffle(b_pool)
    selected = [(p, "A") for p in a_pool[:3]] + [(p, "B") for p in b_pool[:3]]
    rng.shuffle(selected)
    _ = question_id
    return selected


def pick_assigned(
    personas: list[Persona],
    rng: random.Random,
    sides: list[str],
) -> list[tuple[Persona, str]] | None:
    if len(personas) < len(sides):
        return None
    pool = list(personas)
    rng.shuffle(pool)
    return list(zip(pool[: len(sides)], sides, strict=True))


def run_room(
    client: ChatClient,
    question: Question,
    members: list[tuple[Persona, str]],
    *,
    protocol: str,
    start_composition: str,
    room_id: str,
    seed: int,
) -> RoomResult:
    rng = random.Random(seed)
    agents = [
        AgentState(persona=persona, assigned_side=side, stances=[side])
        for persona, side in members
    ]
    turns: list[Turn] = []
    a_counts = [sum(1 for agent in agents if agent.stances[-1] == "A")]

    if protocol == "opening_argued":
        for agent in agents:
            side_text = (
                question.position_a.ko
                if agent.assigned_side == "A"
                else question.position_b.ko
            )
            first, second = question.position_a, question.position_b
            messages = [
                {
                    "role": "system",
                    "content": system_for_persona(agent.persona, "full"),
                },
                {
                    "role": "user",
                    "content": opening_user(
                        question,
                        first,
                        second,
                        agent.persona.name,
                        side_text,
                    ),
                },
            ]
            result = client.chat(messages, temperature=1.0, max_tokens=220)
            text = parse_public(result.text)
            visible = [other.persona.id for other in agents]
            turns.append(
                Turn(
                    round_index=0,
                    speaker_id=agent.persona.id,
                    speaker_name=agent.persona.name,
                    text=text,
                    visible_to=visible,
                )
            )

    for round_index in range(1, 4):
        order = list(range(len(agents)))
        rng.shuffle(order)
        for agent_index in order:
            agent = agents[agent_index]
            viewer = agent.persona.id if protocol == "monologue" else None
            transcript = format_transcript(turns, viewer)
            first, second = question.position_a, question.position_b
            side = None
            if protocol == "side_restated" and round_index == 1:
                side = (
                    question.position_a.ko
                    if agent.assigned_side == "A"
                    else question.position_b.ko
                )
            messages = [
                {
                    "role": "system",
                    "content": system_for_persona(agent.persona, "full"),
                },
                {
                    "role": "user",
                    "content": speech_user(
                        question,
                        first,
                        second,
                        agent.persona.name,
                        transcript,
                        side=side,
                    ),
                },
            ]
            result = client.chat(messages, temperature=1.0, max_tokens=220)
            text = parse_public(result.text)
            if protocol == "monologue":
                visible = [agent.persona.id]
            else:
                visible = [other.persona.id for other in agents]
            turns.append(
                Turn(
                    round_index=round_index,
                    speaker_id=agent.persona.id,
                    speaker_name=agent.persona.name,
                    text=text,
                    visible_to=visible,
                )
            )
        for agent in agents:
            viewer = agent.persona.id if protocol == "monologue" else None
            transcript = format_transcript(turns, viewer)
            record: SurveyRecord = run_survey_item(
                client,
                question,
                persona=agent.persona,
                condition="full",
                transcript=transcript,
                temperature=0.0,
            )
            agent.stances.append(record.choice)
        a_counts.append(sum(1 for agent in agents if agent.stances[-1] == "A"))

    return RoomResult(
        room_id=room_id,
        question_id=question.id,
        protocol=protocol,
        start_composition=start_composition,
        agents=agents,
        turns=turns,
        a_counts=a_counts,
    )
