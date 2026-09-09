"""Run the 4-setting × 3-risk PRISK mini-evaluation and write JSON artifacts."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prisk.dataset import seed_cases
from prisk.generators import (
    Generator,
    HuggingFaceGenerator,
    MockGenerator,
    build_prompt,
)
from prisk.metrics import (
    coverage_rate,
    covered_answers,
    irp_score,
    normalize_1_to_5,
    personalization_induced_sycophancy,
    relative_coverage,
    sycophancy_score,
    useful_item_recall,
)
from prisk.paper_results import (
    PAPER_BENCHMARK_ACCURACY,
    PAPER_TABLE_2,
    paper_mean_drops,
)
from prisk.retrieval import memories_for_setting
from prisk.schemas import SETTINGS, GenerationResult, ScoredResult, SeedCase, Setting


def score_generation(
    case: SeedCase,
    generation: GenerationResult,
    base_coverage_n: int | None = None,
) -> ScoredResult:
    scored = ScoredResult(generation=generation)
    if case.risk_type == "irrelevant_personalization":
        raw, flags = irp_score(generation.response, case)
        scored.irp_score = raw
        scored.flags = flags
        return scored
    if case.risk_type == "preference_narrowing":
        covered = covered_answers(generation.response, case.universal_answers)
        scored.covered_answers = covered
        scored.coverage_rate = coverage_rate(covered, case.universal_answers)
        scored.uir = useful_item_recall(covered, case.useful_answers)
        if base_coverage_n is not None:
            scored.relative_coverage = relative_coverage(len(covered), base_coverage_n)
        return scored
    raw, flags = sycophancy_score(generation.response, case)
    scored.syco_score = raw
    scored.pis_score = personalization_induced_sycophancy(generation.response, case)
    scored.flags = flags
    return scored


def run_case(
    case: SeedCase,
    generator: Generator,
    top_k: int = 3,
) -> dict[Setting, ScoredResult]:
    by_setting: dict[Setting, ScoredResult] = {}
    base_n: int | None = None
    for setting in SETTINGS:
        decision, memories = memories_for_setting(case, setting, top_k=top_k)
        prompt = build_prompt(case, setting, memories)
        response = generator.generate(case, setting, prompt, memories)
        generation = GenerationResult(
            record_id=case.record_id,
            risk_type=case.risk_type,
            setting=setting,
            question=case.question,
            prompt=prompt,
            response=response,
            backend=generator.name,
            model_name=generator.model_name,
            router_decision=decision,
            retrieved_memories=[memory.text for memory in memories],
        )
        scored = score_generation(case, generation, base_coverage_n=base_n)
        if setting == "base" and scored.covered_answers is not None:
            base_n = len(scored.covered_answers)
        by_setting[setting] = scored
    # RelCR needs the base coverage count; recompute personalized rows.
    if case.risk_type == "preference_narrowing" and base_n is not None:
        for setting, scored in by_setting.items():
            if setting == "base":
                scored.relative_coverage = 1.0
            else:
                scored.relative_coverage = relative_coverage(
                    len(scored.covered_answers), base_n
                )
    return by_setting


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def aggregate(rows: list[ScoredResult]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[ScoredResult]] = defaultdict(list)
    for row in rows:
        grouped[(row.generation.risk_type, row.generation.setting)].append(row)
    table: list[dict[str, Any]] = []
    for (risk_type, setting), items in sorted(grouped.items()):
        irp = _mean(
            [
                normalize_1_to_5(item.irp_score)
                for item in items
                if item.irp_score is not None
            ]
        )
        uir = _mean([item.uir * 100.0 for item in items if item.uir is not None])
        syco = _mean(
            [
                normalize_1_to_5(item.syco_score)
                for item in items
                if item.syco_score is not None
            ]
        )
        pis = _mean(
            [
                (1.0 - item.pis_score) * 100.0
                for item in items
                if item.pis_score is not None
            ]
        )
        table.append(
            {
                "risk_type": risk_type,
                "setting": setting,
                "n": len(items),
                "irp_resistance_pct": irp,
                "uir_pct": uir,
                "syco_resistance_pct": syco,
                "pis_noninduced_pct": pis,
            }
        )
    return {"rows": table}


def _serialize_scored(row: ScoredResult) -> dict[str, Any]:
    payload = asdict(row)
    payload["generation"]["risk_type"] = row.generation.risk_type
    payload["generation"]["setting"] = row.generation.setting
    return payload


def run_replication(
    backend: str = "mock",
    hf_model: str = "Qwen/Qwen3.5-4B:featherless-ai",
    out_dir: Path | None = None,
) -> dict[str, Any]:
    generator: Generator
    notes: list[str] = []
    if backend == "hf":
        try:
            generator = HuggingFaceGenerator(model_name=hf_model)
            generator.generate(
                seed_cases()[0],
                "base",
                seed_cases()[0].question,
                [],
            )
        except Exception as exc:
            notes.append(f"Hugging Face backend failed ({exc}); using mock generator.")
            generator = MockGenerator()
    else:
        generator = MockGenerator()
        notes.append(
            "Mock generator used. Qwen3.5-4B via Hugging Face is optional "
            "with --backend hf."
        )

    cases = seed_cases()
    scored_rows: list[ScoredResult] = []
    playground: list[dict[str, Any]] = []
    for case in cases:
        by_setting = run_case(case, generator)
        for setting, scored in by_setting.items():
            scored_rows.append(scored)
            playground.append(
                {
                    "record_id": case.record_id,
                    "risk_type": case.risk_type,
                    "domain": case.domain,
                    "question": case.question,
                    "persona": case.profile.persona,
                    "persona_id": case.profile.persona_id,
                    "attributes": case.profile.attributes,
                    "setting": setting,
                    "prompt": scored.generation.prompt,
                    "response": scored.generation.response,
                    "irp_score": scored.irp_score,
                    "irp_resistance_pct": (
                        None
                        if scored.irp_score is None
                        else round(normalize_1_to_5(scored.irp_score), 2)
                    ),
                    "uir_pct": None
                    if scored.uir is None
                    else round(scored.uir * 100.0, 2),
                    "coverage_rate": scored.coverage_rate,
                    "relative_coverage": scored.relative_coverage,
                    "syco_score": scored.syco_score,
                    "syco_resistance_pct": (
                        None
                        if scored.syco_score is None
                        else round(normalize_1_to_5(scored.syco_score), 2)
                    ),
                    "pis_score": scored.pis_score,
                    "flags": scored.flags,
                    "covered_answers": scored.covered_answers,
                    "universal_answers": list(case.universal_answers),
                    "useful_answers": list(case.useful_answers),
                    "router_decision": scored.generation.router_decision,
                    "retrieved_memories": list(scored.generation.retrieved_memories),
                    "user_is_at_fault": case.user_is_at_fault,
                    "stated_preference": case.stated_preference,
                    "preferences": list(case.profile.preferences),
                }
            )

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "backend": generator.name,
        "model_name": generator.model_name,
        "notes": notes,
        "n_cases": len(cases),
        "n_generations": len(scored_rows),
        "aggregate": aggregate(scored_rows),
        "paper_table_2": PAPER_TABLE_2,
        "paper_mean_drops": paper_mean_drops(),
        "paper_benchmark_accuracy": PAPER_BENCHMARK_ACCURACY,
        "takeaways": _takeaways(aggregate(scored_rows)["rows"]),
        "playground": playground,
        "results": [_serialize_scored(row) for row in scored_rows],
    }
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "replication_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        dashboard_dir = Path(__file__).resolve().parents[1] / "dashboard" / "data"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        (dashboard_dir / "replication.json").write_text(
            json.dumps(dashboard_payload(summary), indent=2),
            encoding="utf-8",
        )
    return summary


def dashboard_payload(summary: dict[str, Any]) -> dict[str, Any]:
    """JSON for the Next.js dashboard: same summary, without per-row traces."""
    return {key: value for key, value in summary.items() if key != "results"}


def _takeaways(rows: list[dict[str, Any]]) -> list[str]:
    by_risk: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_risk[row["risk_type"]][row["setting"]] = row
    lines: list[str] = []
    mapping = {
        "irrelevant_personalization": "irp_resistance_pct",
        "preference_narrowing": "uir_pct",
        "sycophantic_bias": "syco_resistance_pct",
    }
    labels = {
        "irrelevant_personalization": "irrelevant personalization resistance",
        "preference_narrowing": "useful-item recall",
        "sycophantic_bias": "sycophancy resistance",
    }
    for risk, metric in mapping.items():
        base = by_risk[risk].get("base", {}).get(metric)
        profile = by_risk[risk].get("profile_only", {}).get(metric)
        if base is None or profile is None:
            continue
        drop = base - profile
        lines.append(
            f"{labels[risk]} dropped {drop:.1f} points from base ({base:.1f}) "
            f"to profile-only ({profile:.1f}) on the mini-benchmark."
        )
    return lines
