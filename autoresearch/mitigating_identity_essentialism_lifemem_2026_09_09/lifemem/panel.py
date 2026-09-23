from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from random import Random

from lifemem.statements import profile_paragraph, qa_to_statements
from lifemem.types import (
    AgentProfile,
    AgentState,
    LifeEvent,
    SurveyOption,
    SurveyQuestion,
)

LIKERT = (
    SurveyOption("1", "Strongly disagree"),
    SurveyOption("2", "Disagree"),
    SurveyOption("3", "Neither agree nor disagree"),
    SurveyOption("4", "Agree"),
    SurveyOption("5", "Strongly agree"),
)
FREQ = (
    SurveyOption("1", "Never"),
    SurveyOption("2", "Rarely"),
    SurveyOption("3", "Sometimes"),
    SurveyOption("4", "Often"),
    SurveyOption("5", "Very often"),
)

EVAL_SPECS: tuple[tuple[str, str, str, tuple[SurveyOption, ...]], ...] = (
    ("POLINT", "Politics", "You are interested in political affairs.", LIKERT),
    ("TRUST", "Values", "Most people can be trusted.", LIKERT),
    ("LIFESAT", "Wellbeing", "You are satisfied with your life as a whole.", LIKERT),
    ("HLTH", "Health", "In general, your health is excellent.", LIKERT),
    (
        "NEIGH",
        "Housing",
        "You would like to stay in your current neighbourhood.",
        LIKERT,
    ),
    ("NETUSE", "Media", "The internet is important in your daily life.", LIKERT),
    ("CIVIC", "Community", "You take part in local groups or volunteering.", LIKERT),
    ("FINSTR", "Finances", "You have been under financial strain recently.", LIKERT),
)

EVENT_BANK: tuple[tuple[str, str, str, tuple[str, ...], dict[str, int]], ...] = (
    (
        "HLT",
        "Health",
        "How often have you had trouble sleeping?",
        ("health", "sleep"),
        {"HLTH": -1, "LIFESAT": -1},
    ),
    (
        "JOB",
        "Work",
        "Have you been promoted or given more responsibility at work?",
        ("work", "promotion"),
        {"FINSTR": -1, "LIFESAT": 1, "POLINT": 1},
    ),
    (
        "UNEMP",
        "Work",
        "Have you been unemployed and looking for work?",
        ("work", "unemployment"),
        {"FINSTR": 1, "LIFESAT": -1, "TRUST": -1},
    ),
    (
        "SCHOOL",
        "Education",
        "Have you enrolled in or completed a new educational programme?",
        ("school", "education"),
        {"NETUSE": 1, "POLINT": 1, "NEIGH": -1},
    ),
    (
        "MOVE",
        "Housing",
        "Have you moved to a different city or region?",
        ("housing", "migration"),
        {"NEIGH": -1, "CIVIC": -1, "NETUSE": 1},
    ),
    (
        "MARRY",
        "Family",
        "Have you gotten married or started living with a partner?",
        ("family", "marriage"),
        {"LIFESAT": 1, "CIVIC": 1, "NEIGH": 1},
    ),
    (
        "CHILD",
        "Family",
        "Has a child been born or joined your household?",
        ("family", "child"),
        {"FINSTR": 1, "CIVIC": -1, "LIFESAT": 1},
    ),
    (
        "ILL",
        "Health",
        "Has a close family member had a serious illness?",
        ("family", "illness"),
        {"HLTH": -1, "TRUST": 1, "CIVIC": 1},
    ),
    (
        "VOL",
        "Community",
        "Have you started volunteering or community work?",
        ("civic", "volunteer"),
        {"CIVIC": 1, "POLINT": 1, "TRUST": 1},
    ),
    (
        "VOTE",
        "Politics",
        "Have you worked on a political campaign or attended a rally?",
        ("civic", "politics"),
        {"POLINT": 1, "CIVIC": 1, "TRUST": -1},
    ),
    (
        "HOUSE",
        "Housing",
        "Have you bought a home or taken on a housing loan?",
        ("housing", "home"),
        {"FINSTR": 1, "NEIGH": 1, "LIFESAT": 1},
    ),
    (
        "HARD",
        "Finances",
        "Has your household had trouble paying bills?",
        ("finance", "hardship"),
        {"FINSTR": 1, "LIFESAT": -1, "HLTH": -1},
    ),
)

SES_MEANS = {
    "low": (-0.7, -0.4, -0.5, -0.6, -0.2, -0.3, -0.4, 0.8),
    "middle": (0.0, 0.1, 0.0, 0.1, 0.0, 0.2, 0.1, 0.0),
    "high": (0.8, 0.5, 0.6, 0.5, 0.3, 0.4, 0.5, -0.7),
}

WAVES = (
    (1, 1995, "adolescence"),
    (2, 1996, "late adolescence"),
    (3, 2002, "early adulthood"),
    (4, 2008, "early career"),
    (5, 2016, "established adulthood"),
    (6, 2023, "early midlife"),
)


@dataclass
class Panel:
    questions: list[SurveyQuestion]
    agents: list[AgentState]
    humans: dict[tuple[str, int, str], str]
    waves: tuple[int, ...]
    events_by_wave: dict[tuple[str, int], list[LifeEvent]]


def _options_for(
    spec: tuple[str, str, str, tuple[SurveyOption, ...]],
) -> SurveyQuestion:
    variable, section, question, options = spec
    return SurveyQuestion(
        variable=variable, section=section, question=question, options=options
    )


def _clip_option(value: float, n_options: int) -> str:
    index = int(round(value))
    index = max(1, min(n_options, index))
    return str(index)


def build_panel(
    n_agents: int = 24,
    n_waves: int = 6,
    events_per_wave: int = 8,
    seed: int = 42,
) -> Panel:
    rng = Random(seed)
    questions = [_options_for(spec) for spec in EVAL_SPECS]
    waves = tuple(wave for wave, _year, _label in WAVES[:n_waves])
    sexes = ("female", "male")
    ses_levels = ("low", "middle", "high")
    educations = ("high school", "some college", "bachelor's degree")
    religions = ("none", "christian", "other")
    regions = ("Northeast", "Midwest", "South", "West")
    occupations = (
        "student",
        "service worker",
        "technician",
        "professional",
        "unemployed",
    )
    agents: list[AgentState] = []
    humans: dict[tuple[str, int, str], str] = {}
    events_by_wave: dict[tuple[str, int], list[LifeEvent]] = {}

    for i in range(n_agents):
        ses = ses_levels[i % 3]
        sex = sexes[i % 2]
        education = educations[i % 3]
        religion = religions[i % 3]
        region = regions[i % 4]
        occupation = occupations[i % 5]
        birth_year = 1978 + (i % 7)
        mean = SES_MEANS[ses]
        offset = tuple(rng.gauss(0.0, 1.05) for _ in questions)
        latent = tuple(m + o for m, o in zip(mean, offset, strict=True))
        fields = {
            "sex": sex,
            "ses": ses,
            "education": education,
            "religion": religion,
            "region": region,
            "birth_year": str(birth_year),
            "occupation": occupation,
        }
        profile = AgentProfile(
            agent_id=f"A{i:03d}",
            sex=sex,
            ses=ses,
            education=education,
            religion=religion,
            region=region,
            birth_year=birth_year,
            occupation=occupation,
            latent=latent,
            profile_text=profile_paragraph(fields),
        )
        agent = AgentState(profile=profile)
        running = list(latent)
        for wave_idx, wave in enumerate(waves):
            chosen = rng.sample(EVENT_BANK, k=min(events_per_wave, len(EVENT_BANK)))
            wave_events: list[LifeEvent] = []
            for event_idx, (code, section, question, tags, deltas) in enumerate(chosen):
                intensity = rng.choice([2, 3, 4, 5])
                sign = 1 if intensity >= 3 else -1
                for variable, delta in deltas.items():
                    q_pos = next(
                        j for j, q in enumerate(questions) if q.variable == variable
                    )
                    running[q_pos] += 0.22 * sign * delta
                answer_code = str(intensity)
                answer_text = FREQ[intensity - 1].text
                second, first = qa_to_statements(question, answer_text)
                event = LifeEvent(
                    event_id=f"{profile.agent_id}-w{wave}-{code}-{event_idx}",
                    agent_id=profile.agent_id,
                    wave=wave,
                    section=section,
                    question=question,
                    answer_code=answer_code,
                    answer_text=answer_text,
                    statement=second,
                    first_person=first,
                    tags=tags,
                )
                wave_events.append(event)
            events_by_wave[(profile.agent_id, wave)] = wave_events
            for q_idx, question in enumerate(questions):
                noise = rng.gauss(0.0, 0.35)
                humans[(profile.agent_id, wave, question.variable)] = _clip_option(
                    3 + running[q_idx] + 0.08 * wave_idx + noise,
                    len(question.options),
                )
        agents.append(agent)

    return Panel(
        questions=questions,
        agents=agents,
        humans=humans,
        waves=waves,
        events_by_wave=events_by_wave,
    )


def panel_to_dict(panel: Panel) -> dict:
    return {
        "waves": list(panel.waves),
        "questions": [
            {
                "variable": q.variable,
                "section": q.section,
                "question": q.question,
                "options": [{"code": o.code, "text": o.text} for o in q.options],
            }
            for q in panel.questions
        ],
        "agents": [
            {
                "agent_id": agent.profile.agent_id,
                "sex": agent.profile.sex,
                "ses": agent.profile.ses,
                "education": agent.profile.education,
                "religion": agent.profile.religion,
                "region": agent.profile.region,
                "birth_year": agent.profile.birth_year,
                "occupation": agent.profile.occupation,
                "profile_text": agent.profile.profile_text,
                "latent": list(agent.profile.latent),
            }
            for agent in panel.agents
        ],
        "events": [
            {
                "event_id": event.event_id,
                "agent_id": event.agent_id,
                "wave": event.wave,
                "section": event.section,
                "question": event.question,
                "answer_code": event.answer_code,
                "answer_text": event.answer_text,
                "statement": event.statement,
                "first_person": event.first_person,
                "tags": list(event.tags),
            }
            for events in panel.events_by_wave.values()
            for event in events
        ],
        "humans": [
            {
                "agent_id": agent_id,
                "wave": wave,
                "variable": variable,
                "answer": answer,
            }
            for (agent_id, wave, variable), answer in sorted(panel.humans.items())
        ],
    }


def save_panel(panel: Panel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(panel_to_dict(panel), indent=2), encoding="utf-8")
