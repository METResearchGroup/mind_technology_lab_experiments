from __future__ import annotations

from analyze import analyze
from dummy import DummyClient, make_synthetic_pool
from parse import parse_choice
from questions import QUESTION_BY_ID
from survey import run_survey_item


def test_synthetic_pool_fills_160_cells() -> None:
    pool = make_synthetic_pool(per_cell=1)
    assert len(pool) == 160
    assert len({persona.cell for persona in pool}) == 160


def test_dummy_survey_returns_a_or_b() -> None:
    pool = make_synthetic_pool(per_cell=1)
    question = QUESTION_BY_ID["clim_tech"]
    record = run_survey_item(
        DummyClient(),
        question,
        persona=pool[0],
        condition="full",
    )
    assert record.choice in {"A", "B"}


def test_dummy_choice_parses_korean_json() -> None:
    question = QUESTION_BY_ID["env_priority"]
    client = DummyClient()
    result = client.chat(
        [
            {"role": "system", "content": "지정된 JSON 형식으로만 답하십시오."},
            {
                "role": "user",
                "content": (
                    f"[쟁점] {question.topic_ko}\n"
                    f"- {question.position_a.ko}\n"
                    f"- {question.position_b.ko}\n"
                    '{"choice": "..."}'
                ),
            },
        ],
        temperature=0.0,
        max_tokens=32,
    )
    assert parse_choice(result.text, question.position_a, question.position_b) in {
        "A",
        "B",
    }


def test_analyze_empty_survey_uses_paper_findings() -> None:
    pool = make_synthetic_pool(per_cell=1)
    payload = analyze(pool, [], [], client_label="dummy-client (paper-calibrated)")
    assert payload["paper"]["id"] == "2609.07573"
    assert payload["survey"]["mean_group_gap"] is None
    assert payload["takeaways"][0]["id"] == "representation"
    assert payload["replication"]["n_personas"] == 160


def test_dummy_takeaways_do_not_claim_qwen() -> None:
    pool = make_synthetic_pool(per_cell=1)
    question_id = "clim_tech"
    survey = [
        {
            "condition": "full",
            "persona_id": persona.id,
            "question_id": question_id,
            "choice": "A",
        }
        for persona in pool
    ]
    payload = analyze(
        pool,
        survey,
        [],
        client_label="dummy-client (paper-calibrated)",
    )
    body = payload["takeaways"][0]["body"]
    assert "dummy client" in body
    assert "Qwen3.5-4B" not in body


def test_qwen_analyze_note_is_live() -> None:
    pool = make_synthetic_pool(per_cell=1)[:20]
    survey = [
        {
            "condition": "full",
            "persona_id": persona.id,
            "question_id": "clim_tech",
            "choice": "B" if index % 2 else "A",
        }
        for index, persona in enumerate(pool)
    ]
    payload = analyze(pool, survey, [], client_label="Qwen/Qwen3.5-4B")
    assert payload["replication"]["offline"] is False
    assert payload["replication"]["n_personas"] == 20
    assert payload["replication"]["cells"] == 20
    assert "Qwen3.5-4B" in payload["replication"]["note"]
    assert "dummy client" not in payload["replication"]["note"]
    assert "Qwen3.5-4B persona A-shares" in payload["takeaways"][0]["body"]


def _room(
    room_id: str,
    question_id: str,
    protocol: str,
    movement_stances: list[list[str]],
) -> dict:
    return {
        "room_id": room_id,
        "question_id": question_id,
        "protocol": protocol,
        "start_composition": "balanced",
        "a_counts": [3, 3, 3, 3],
        "agents": [
            {
                "persona_id": f"p{index}",
                "name": f"agent{index}",
                "assigned_side": stances[0],
                "stances": stances,
            }
            for index, stances in enumerate(movement_stances)
        ],
        "turns": [],
    }


def test_qwen_restated_takeaway_title_follows_movement() -> None:
    pool = make_synthetic_pool(per_cell=1)[:6]
    survey = [
        {
            "condition": "full",
            "persona_id": persona.id,
            "question_id": "clim_tech",
            "choice": "A",
        }
        for persona in pool
    ]
    moved = [["A", "A", "B", "B"] for _ in range(6)]
    rooms = [
        _room("r-debate", "clim_tech", "debate", moved),
        _room("r-restated", "clim_tech", "side_restated", moved),
    ]
    payload = analyze(pool, survey, rooms, client_label="Qwen/Qwen3.5-4B")
    anchor = next(item for item in payload["takeaways"] if item["id"] == "anchor")
    assert anchor["title"] == "Restating a starting side did not freeze updating"
