"""Turn raw survey and room files into the dashboard payload."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from metrics import (
    a_share,
    concentration_flags,
    direction_matches,
    group_rows,
    is_divisive,
    mean,
    mean_absolute_gap,
    movement_rate,
)
from paper_tables import (
    PAPER_FINDINGS,
    PAPER_LLM_BY_GROUP,
    PAPER_TABLE3,
    PAPER_TABLE6,
    PAPER_TABLE7,
)
from personas import Persona
from questions import PAPER_GPT41MINI_OVERALL, QUESTION_BY_ID, QUESTIONS
from survey import choice_from_raw


def _choices_for_condition(
    records: list[dict[str, Any]], condition: str
) -> dict[str, dict[str, str | None]]:
    by_question: dict[str, dict[str, str | None]] = defaultdict(dict)
    for record in records:
        if record.get("condition") != condition:
            continue
        persona_id = record.get("persona_id") or f"anon:{record['question_id']}"
        by_question[record["question_id"]][persona_id] = record.get("choice")
    return by_question


def summarize_live_sample(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_question: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record.get("condition") != "full":
            continue
        question = QUESTION_BY_ID.get(record.get("question_id") or "")
        if question is None:
            continue
        choice = record.get("choice")
        if choice not in {"A", "B"}:
            raw = record.get("raw") or ""
            order = record.get("order") or "AB"
            choice = choice_from_raw(raw, question, order)
        if choice in {"A", "B"}:
            by_question[record["question_id"]].append(choice)
    rows = []
    for question in QUESTIONS:
        values = by_question.get(question.id, [])
        rows.append(
            {
                "question_id": question.id,
                "n": len(values),
                "persona_share": a_share(values),
                "paper_gpt41mini": PAPER_GPT41MINI_OVERALL[question.id],
                "human_overall": question.human_overall,
            }
        )
    return rows


def analyze(
    personas: list[Persona],
    survey_records: list[dict[str, Any]],
    rooms: list[dict[str, Any]],
    *,
    client_label: str = "Qwen/Qwen3.5-4B",
    live_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    persona_by_id = {persona.id: persona for persona in personas}
    full = _choices_for_condition(survey_records, "full")
    questions_out: list[dict[str, Any]] = []
    all_group_rows = []
    overall_gaps: list[float] = []
    for question in QUESTIONS:
        choices = full.get(question.id, {})
        ordered = [choices.get(persona.id) for persona in personas]
        share = a_share(ordered)
        rows = group_rows(question, personas, choices)
        all_group_rows.extend(rows)
        mag = mean_absolute_gap(rows)
        if share is not None:
            overall_gaps.append(abs(share - question.human_overall))
        questions_out.append(
            {
                "id": question.id,
                "domain": question.domain,
                "topic_en": question.topic_en,
                "topic_ko": question.topic_ko,
                "position_a_en": question.position_a.en,
                "position_b_en": question.position_b.en,
                "position_a_ko": question.position_a.ko,
                "position_b_ko": question.position_b.ko,
                "human_overall": question.human_overall,
                "paper_gpt41mini": PAPER_GPT41MINI_OVERALL[question.id],
                "paper_groups": [
                    {
                        "axis": axis,
                        "group": group,
                        "persona_share": share,
                        "human_share": question.human_by_group.get(axis, {}).get(group),
                    }
                    for axis, groups in PAPER_LLM_BY_GROUP.get(question.id, {}).items()
                    for group, share in groups.items()
                ],
                "persona_overall": share,
                "divisive": is_divisive(share),
                "mean_group_gap": mag,
                "groups": [
                    {
                        "axis": row.axis,
                        "group": row.group,
                        "persona_share": row.persona_share,
                        "human_share": row.human_share,
                        "n": row.n,
                    }
                    for row in rows
                ],
            }
        )

    matches, total = direction_matches(all_group_rows)
    control_overall = []
    for condition in ("demographics", "citizen", "none"):
        cond_map = _choices_for_condition(survey_records, condition)
        for question in QUESTIONS:
            values = list(cond_map.get(question.id, {}).values())
            share = a_share(values)
            control_overall.append(
                {
                    "condition": condition,
                    "question_id": question.id,
                    "persona_share": share,
                    "human_overall": question.human_overall,
                    "n": len([item for item in values if item in {"A", "B"}]),
                }
            )

    rooms_out = []
    for room in rooms:
        start = []
        end = []
        agents_out = []
        for agent in room["agents"]:
            stances = agent["stances"]
            start.append(stances[0] if stances else None)
            end.append(stances[-1] if stances else None)
            persona = persona_by_id.get(agent["persona_id"])
            agents_out.append(
                {
                    "id": agent["persona_id"],
                    "name": agent["name"],
                    "sex": persona.sex if persona else None,
                    "age": persona.age if persona else None,
                    "education": persona.education if persona else None,
                    "region": persona.region if persona else None,
                    "assigned_side": agent["assigned_side"],
                    "stances": stances,
                }
            )
        rooms_out.append(
            {
                "room_id": room["room_id"],
                "question_id": room["question_id"],
                "protocol": room["protocol"],
                "start_composition": room["start_composition"],
                "a_counts": room["a_counts"],
                "movement": movement_rate(start, end),
                "agents": agents_out,
                "turns": room["turns"],
            }
        )

    debate_vs_mono = []
    for question in QUESTIONS:
        debate = [
            room
            for room in rooms_out
            if room["question_id"] == question.id
            and room["protocol"] == "debate"
            and room["start_composition"] == "balanced"
        ]
        mono = [
            room
            for room in rooms_out
            if room["question_id"] == question.id
            and room["protocol"] == "monologue"
            and room["start_composition"] == "balanced"
        ]
        if not debate or not mono:
            continue
        debate_final = mean(float(room["a_counts"][-1]) for room in debate)
        mono_final = mean(float(room["a_counts"][-1]) for room in mono)
        debate_vs_mono.append(
            {
                "question_id": question.id,
                "debate_final_a": debate_final,
                "monologue_final_a": mono_final,
                "difference": (
                    None
                    if debate_final is None or mono_final is None
                    else debate_final - mono_final
                ),
                "debate_movement": mean(
                    room["movement"] for room in debate if room["movement"] is not None
                ),
                "monologue_movement": mean(
                    room["movement"] for room in mono if room["movement"] is not None
                ),
            }
        )

    mag = mean_absolute_gap(all_group_rows)
    synthetic = any(persona.id.startswith("synth-") for persona in personas)
    n_cells = len({persona.cell for persona in personas})
    takeaways = _takeaways(
        mag=mag,
        overall_gap=mean(overall_gaps),
        direction=(matches, total),
        concentrated=concentration_flags(all_group_rows),
        questions_out=questions_out,
        debate_vs_mono=debate_vs_mono,
        rooms_out=rooms_out,
        n_survey=sum(1 for row in survey_records if row.get("condition") == "full"),
        client_label=client_label,
    )
    return {
        "paper": {
            "id": "2609.07573",
            "title": (
                "From Simulated Citizens to Simulated Deliberation: "
                "Challenges in Representation and Interaction"
            ),
            "url": "https://arxiv.org/abs/2609.07573",
            "alphaxiv": "https://www.alphaxiv.org/abs/2609.07573",
            "findings": PAPER_FINDINGS,
            "table3": PAPER_TABLE3,
            "table6": PAPER_TABLE6,
            "table7": PAPER_TABLE7,
        },
        "replication": {
            "model": client_label,
            "provider": "featherless-ai" if "Qwen" in client_label else "offline",
            "n_personas": len(personas),
            "cells": n_cells,
            "per_cell": 1,
            "language": "ko",
            "persona_source": "synthetic" if synthetic else "nemotron-korea",
            "n_survey_full": sum(
                1 for row in survey_records if row.get("condition") == "full"
            ),
            "n_rooms": len(rooms),
            "offline": "dummy" in client_label.lower(),
            "note": (
                "The paper used 640 personas (4 per cell) and GPT-4.1-mini. "
                f"This run uses {len(personas)} personas spread across "
                f"{n_cells} sex x age x education x region cells. "
                + (
                    "Survey and debate rows below come from a deterministic "
                    "dummy client calibrated to the paper's GPT-4.1-mini "
                    "overall A-shares, because a full live Qwen run was not "
                    "used for this payload."
                    if "dummy" in client_label.lower()
                    else (
                        "Survey and debate rows below come from Qwen3.5-4B, "
                        "the lab default open model. Group shares are noisy "
                        f"at n={len(personas)}."
                    )
                )
            ),
        },
        "survey": {
            "mean_group_gap": mag,
            "mean_overall_gap": mean(overall_gaps),
            "direction_matches": matches,
            "direction_total": total,
            "near_unanimous_groups": concentration_flags(all_group_rows),
            "questions": questions_out,
            "controls": control_overall,
            "live_qwen_sample": summarize_live_sample(live_records or []),
        },
        "deliberation": {
            "debate_vs_monologue": debate_vs_mono,
            "rooms": rooms_out,
        },
        "takeaways": takeaways,
    }


def _takeaways(
    *,
    mag: float | None,
    overall_gap: float | None,
    direction: tuple[int, int],
    concentrated: int,
    questions_out: list[dict[str, Any]],
    debate_vs_mono: list[dict[str, Any]],
    rooms_out: list[dict[str, Any]],
    n_survey: int,
    client_label: str,
) -> list[dict[str, str]]:
    if n_survey == 0:
        return [dict(item) for item in PAPER_FINDINGS]
    matches, total = direction
    dummy = "dummy" in client_label.lower()
    source = (
        "a dummy client calibrated to the paper's overall GPT-4.1-mini A-shares"
        if dummy
        else "Qwen3.5-4B persona A-shares"
    )
    items: list[dict[str, str]] = []
    if mag is not None:
        items.append(
            {
                "id": "representation",
                "title": "Persona answers miss the survey map",
                "body": (
                    f"Across demographic groups, the mean absolute gap between "
                    f"{source} and the human surveys is {mag:.1f} points. "
                    f"The paper reported 29 points with GPT-4.1-mini on 640 "
                    f"personas."
                ),
            }
        )
    if total:
        items.append(
            {
                "id": "direction",
                "title": "Demographic direction is often reversed",
                "body": (
                    f"When the human survey has one group higher than another, "
                    f"the personas match that direction in {matches} of {total} "
                    f"comparisons. The paper matched 34 of 110."
                ),
            }
        )
    items.append(
        {
            "id": "concentration",
            "title": "Answers pile up near 0% or 100%",
            "body": (
                f"{concentrated} demographic cells land within 2 points of 0 or "
                f"100, while the matching human shares stay closer to the middle."
            ),
        }
    )
    if debate_vs_mono:
        mean_diff = mean(
            abs(row["difference"])
            for row in debate_vs_mono
            if row["difference"] is not None
        )
        if mean_diff is not None:
            body = (
                "Dummy rooms are a protocol walkthrough with hash-based replies, "
                "not a language-model interaction test. In the paper, sealed "
                "monologue rooms ended within one agent of full debate."
                if dummy
                else (
                    f"On balanced rooms, the mean gap between debate and "
                    f"sealed-monologue final A counts is {mean_diff:.2f} "
                    f"agents out of 6. The paper's differences were at most "
                    f"one agent."
                )
            )
            items.append(
                {
                    "id": "interaction",
                    "title": "Sealed monologues land in the same place",
                    "body": body,
                }
            )
    restated = [
        room
        for room in rooms_out
        if room["protocol"] == "side_restated" and room["movement"] is not None
    ]
    if restated:
        moved = mean(
            room["movement"] for room in restated if room["movement"] is not None
        )
        natural = mean(
            room["movement"]
            for room in rooms_out
            if room["protocol"] == "debate" and room["movement"] is not None
        )
        if moved is not None and natural is not None:
            body = (
                "Dummy movement does not drop when round 1 restates the assigned "
                "side. In the paper, restating the side cut later movement to "
                "0 to 3%."
                if dummy
                else (
                    f"When round 1 names the assigned side, mean movement is "
                    f"{100 * moved:.0f}% of agents. In the natural debate "
                    f"protocol it is {100 * natural:.0f}%."
                )
            )
            items.append(
                {
                    "id": "anchor",
                    "title": "Restating a starting side freezes updating",
                    "body": body,
                }
            )
    items.append(
        {
            "id": "use",
            "title": "Treat argument surfacing as a separate job",
            "body": (
                "The transcripts still give reasons on both sides. That can help "
                "a reader inspect arguments. It does not show that the room "
                "represents a population, or that peer exchange caused the "
                "stance changes."
            ),
        }
    )
    _ = questions_out
    _ = overall_gap
    return items


def write_dashboard_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
