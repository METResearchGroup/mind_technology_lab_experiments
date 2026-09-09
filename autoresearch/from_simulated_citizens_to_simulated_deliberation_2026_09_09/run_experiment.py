"""Run the scaled Qwen3.5-4B replication of arXiv:2609.07573."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from analyze import analyze, write_dashboard_payload
from client import ChatClient, QwenClient, map_parallel
from debate import pick_assigned, pick_balanced_agents, run_room
from dummy import DummyClient, make_synthetic_pool
from personas import (
    Persona,
    load_personas,
    sample_balanced_pool,
    save_personas,
    select_spread_subset,
)
from questions import QUESTION_BY_ID, QUESTIONS
from survey import run_survey_item

_WRITE_LOCK = threading.Lock()

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
DASHBOARD_DATA = ROOT / "dashboard" / "public" / "data"


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _survey_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        row.get("condition") or "",
        row.get("persona_id") or "",
        row.get("question_id") or "",
    )


def _result_paths(dummy: bool) -> tuple[Path, Path]:
    if dummy:
        return RESULTS / "survey.jsonl", RESULTS / "rooms.jsonl"
    return RESULTS / "survey_qwen.jsonl", RESULTS / "rooms_qwen.jsonl"


def cmd_sample(per_cell: int, *, allow_synthetic: bool) -> list[Persona]:
    path = DATA / "personas.json"
    if path.exists():
        print(f"loading existing pool {path}")
        return load_personas(path)
    print("sampling balanced persona pool from Nemotron-Personas-Korea")
    try:
        personas = sample_balanced_pool(per_cell=per_cell)
    except Exception as error:
        if not allow_synthetic:
            raise
        print(f"Nemotron sample failed ({error}); using synthetic pool")
        personas = make_synthetic_pool(per_cell=per_cell)
    save_personas(path, personas)
    print(f"wrote {len(personas)} personas to {path}")
    return personas


def cmd_survey(
    client: ChatClient,
    personas: list[Persona],
    *,
    workers: int,
    control_repeats: int,
    path: Path,
) -> list[dict[str, Any]]:
    existing = {_survey_key(row): row for row in _load_jsonl(path)}
    jobs: list[tuple[str, Persona | None, str]] = []
    for persona in personas:
        for question in QUESTIONS:
            key = ("full", persona.id, question.id)
            if key not in existing:
                jobs.append(("full", persona, question.id))
    if control_repeats > 0:
        step = max(1, len(personas) // 40)
        demo_subset = personas[::step][:40]
        for persona in demo_subset:
            for question in QUESTIONS:
                key = ("demographics", persona.id, question.id)
                if key not in existing:
                    jobs.append(("demographics", persona, question.id))
        for index in range(control_repeats):
            dummy = Persona(
                id=f"control-{index:02d}",
                name=f"시민{index:02d}",
                sex="Female",
                sex_ko="여자",
                age=35,
                age_env="30-44",
                age_birth="30s",
                education="college",
                education_ko="대학교",
                region="capital",
                region_ko="서울",
                marital="Married",
                marital_ko="배우자있음",
                occupation="사무직",
                household="부부와 거주",
                narrative="",
            )
            for question in QUESTIONS:
                for condition in ("citizen", "none"):
                    key = (condition, dummy.id, question.id)
                    if key not in existing:
                        jobs.append((condition, dummy, question.id))

    done = 0

    def worker(job: tuple[str, Persona | None, str]) -> dict[str, Any]:
        nonlocal done
        condition, persona, question_id = job
        record = run_survey_item(
            client,
            QUESTION_BY_ID[question_id],
            persona=persona,
            condition=condition,
        )
        row = asdict(record)
        _append_jsonl(path, row)
        with _WRITE_LOCK:
            done += 1
            persona_id = persona.id if persona else "none"
            print(
                f"survey {done}/{len(jobs)} {condition} {question_id} "
                f"{persona_id} choice={record.choice}",
                flush=True,
            )
        return row

    print(f"survey jobs remaining: {len(jobs)}")
    map_parallel(jobs, worker, workers=workers)
    return _load_jsonl(path)


def _choice_map(survey_rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for row in survey_rows:
        if row.get("condition") != "full":
            continue
        if row.get("choice") not in {"A", "B"}:
            continue
        mapping.setdefault(row["question_id"], {})[row["persona_id"]] = row["choice"]
    return mapping


def cmd_debate(
    client: ChatClient,
    personas: list[Persona],
    survey_rows: list[dict[str, Any]],
    *,
    workers: int,
    debate_questions: list[str],
    replicas: int,
    path: Path,
) -> list[dict[str, Any]]:
    existing_ids = {row["room_id"] for row in _load_jsonl(path)}
    choices = _choice_map(survey_rows)
    rng = random.Random(20260909)
    planned: list[dict[str, Any]] = []
    for question_id in debate_questions:
        q_choices = choices.get(question_id, {})
        for replica in range(replicas):
            members = pick_balanced_agents(question_id, personas, q_choices, rng)
            assignment = "survey"
            if members is None:
                members = pick_assigned(personas, rng, ["A", "A", "A", "B", "B", "B"])
                assignment = "forced"
            if members is None:
                continue
            for protocol in ("debate", "monologue"):
                room_id = f"{question_id}-{protocol}-balanced-{replica}"
                planned.append(
                    {
                        "room_id": room_id,
                        "question_id": question_id,
                        "protocol": protocol,
                        "start_composition": "balanced",
                        "assignment": assignment,
                        "members": members,
                    }
                )
        all_a = pick_assigned(personas, rng, ["A"] * 6)
        all_b = pick_assigned(personas, rng, ["B"] * 6)
        if all_a:
            planned.append(
                {
                    "room_id": f"{question_id}-debate-allA-0",
                    "question_id": question_id,
                    "protocol": "debate",
                    "start_composition": "allA",
                    "assignment": "forced",
                    "members": all_a,
                }
            )
        if all_b:
            planned.append(
                {
                    "room_id": f"{question_id}-debate-allB-0",
                    "question_id": question_id,
                    "protocol": "debate",
                    "start_composition": "allB",
                    "assignment": "forced",
                    "members": all_b,
                }
            )
        restated = pick_balanced_agents(question_id, personas, q_choices, rng)
        if restated is None:
            restated = pick_assigned(personas, rng, ["A", "A", "A", "B", "B", "B"])
        if restated:
            planned.append(
                {
                    "room_id": f"{question_id}-side_restated-balanced-0",
                    "question_id": question_id,
                    "protocol": "side_restated",
                    "start_composition": "balanced",
                    "assignment": "survey" if q_choices else "forced",
                    "members": restated,
                }
            )
    jobs = [item for item in planned if item["room_id"] not in existing_ids]
    print(f"rooms planned={len(planned)} remaining={len(jobs)}")

    def worker(item: dict[str, Any]) -> dict[str, Any]:
        result = run_room(
            client,
            QUESTION_BY_ID[item["question_id"]],
            item["members"],
            protocol=item["protocol"],
            start_composition=item["start_composition"],
            room_id=item["room_id"],
            seed=int(hashlib.sha256(item["room_id"].encode()).hexdigest(), 16)
            % 10_000_000,
        )
        row = {
            "room_id": result.room_id,
            "question_id": result.question_id,
            "protocol": result.protocol,
            "start_composition": result.start_composition,
            "a_counts": result.a_counts,
            "agents": [
                {
                    "persona_id": agent.persona.id,
                    "name": agent.persona.name,
                    "assigned_side": agent.assigned_side,
                    "stances": agent.stances,
                }
                for agent in result.agents
            ],
            "turns": [
                {
                    "round_index": turn.round_index,
                    "speaker_id": turn.speaker_id,
                    "speaker_name": turn.speaker_name,
                    "text": turn.text,
                    "visible_to": turn.visible_to,
                }
                for turn in result.turns
            ],
        }
        _append_jsonl(path, row)
        print(f"room done {result.room_id} a_counts={result.a_counts}", flush=True)
        return row

    map_parallel(jobs, worker, workers=max(1, min(workers, 6)))
    return _load_jsonl(path)


def cmd_analyze(
    personas: list[Persona],
    survey_rows: list[dict[str, Any]],
    rooms: list[dict[str, Any]],
    *,
    client_label: str,
    live_records: list[dict[str, Any]] | None = None,
) -> None:
    payload = analyze(
        personas,
        survey_rows,
        rooms,
        client_label=client_label,
        live_records=live_records or [],
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_dashboard_payload(RESULTS / "dashboard.json", payload)
    write_dashboard_payload(DASHBOARD_DATA / "dashboard.json", payload)
    print(f"wrote {RESULTS / 'dashboard.json'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=["sample", "survey", "debate", "analyze", "all"],
        default="all",
        nargs="?",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--per-cell", type=int, default=1)
    parser.add_argument("--control-repeats", type=int, default=24)
    parser.add_argument("--n-personas", type=int, default=None)
    parser.add_argument("--dummy", action="store_true")
    parser.add_argument("--mini", action="store_true")
    parser.add_argument("--no-controls", action="store_true")
    parser.add_argument("--no-synthetic", action="store_true")
    args = parser.parse_args()

    debate_questions = ["clim_tech", "educ_care", "housing", "env_priority"]
    replicas = 2
    control_repeats = 0 if args.no_controls else args.control_repeats
    pool = cmd_sample(args.per_cell, allow_synthetic=not args.no_synthetic)
    personas = pool
    if args.n_personas is not None:
        personas = select_spread_subset(pool, args.n_personas)
        slice_path = DATA / f"personas_n{len(personas)}.json"
        save_personas(slice_path, personas)
        print(f"using {len(personas)} personas spread across cells; wrote {slice_path}")
    survey_personas = personas
    if args.mini:
        debate_questions = ["clim_tech", "educ_care"]
        replicas = 1
        if not args.no_controls:
            control_repeats = min(control_repeats, 8)
        if args.n_personas is None and not args.dummy:
            survey_personas = select_spread_subset(pool, 40)
    if args.n_personas is not None and args.n_personas <= 24:
        debate_questions = ["clim_tech", "educ_care"]
        replicas = 1
    if args.stage == "sample":
        return
    client: ChatClient
    client_label: str
    if args.dummy:
        client = DummyClient()
        client_label = "dummy-client (paper-calibrated)"
    else:
        client = QwenClient()
        client_label = "Qwen/Qwen3.5-4B"
    survey_path, rooms_path = _result_paths(args.dummy)
    survey_rows: list[dict[str, Any]] = _load_jsonl(survey_path)
    rooms: list[dict[str, Any]] = _load_jsonl(rooms_path)
    if args.stage in {"survey", "all"}:
        survey_rows = cmd_survey(
            client,
            survey_personas,
            workers=args.workers,
            control_repeats=control_repeats,
            path=survey_path,
        )
    if args.stage in {"debate", "all"}:
        rooms = cmd_debate(
            client,
            personas,
            survey_rows,
            workers=args.workers,
            debate_questions=debate_questions,
            replicas=replicas,
            path=rooms_path,
        )
    if args.stage in {"analyze", "all"}:
        live_records = _load_jsonl(RESULTS / "live_sample.jsonl") if args.dummy else []
        cmd_analyze(
            survey_personas,
            survey_rows,
            rooms,
            client_label=client_label,
            live_records=live_records,
        )


if __name__ == "__main__":
    main()
