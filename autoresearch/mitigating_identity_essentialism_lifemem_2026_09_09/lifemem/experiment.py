from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from random import Random
from typing import Any

import numpy as np

from lifemem.config import LifeMemConfig
from lifemem.generators import HeuristicRespondent, parse_generation, update_parametric
from lifemem.metrics import pca_2d, response_matrix, silhouette, summarize_method
from lifemem.panel import Panel, build_panel
from lifemem.prompts import (
    build_anti_stereotype,
    build_direct,
    build_full_history,
    build_profile,
    build_retrieval,
)
from lifemem.retrieval import HashedEventEncoder, retrieve_events
from lifemem.types import (
    AgentState,
    GenerationRecord,
    LifeEvent,
    RetrievedEvent,
    SurveyQuestion,
)


def _identity(agent: AgentState) -> dict[str, str]:
    return {
        "sex": agent.profile.sex,
        "ses": agent.profile.ses,
        "education": agent.profile.education,
        "religion": agent.profile.religion,
    }


def _sample_replay(history: list[LifeEvent], size: int, rng: Random) -> list[LifeEvent]:
    if size <= 0 or not history:
        return []
    if len(history) <= size:
        return list(history)
    return rng.sample(history, size)


def _other_events(
    panel: Panel,
    agent_id: str,
    wave: int,
    k: int,
    rng: Random,
) -> list[LifeEvent]:
    pool = [
        event
        for (other_id, event_wave), events in panel.events_by_wave.items()
        if other_id != agent_id and event_wave <= wave
        for event in events
    ]
    if len(pool) <= k:
        return pool
    return rng.sample(pool, k)


def _uses_param(method: str) -> bool:
    return method in {"lifemem", "lifemem_no_struct"}


def _uses_struct(method: str) -> bool:
    return method in {"lifemem", "lifemem_no_param", "event_rag"}


def build_prompt(
    method: str,
    agent: AgentState,
    question: SurveyQuestion,
    retrieved: list[RetrievedEvent],
    config: LifeMemConfig,
) -> str:
    if method == "direct":
        return build_direct(question)
    if method == "profile":
        return build_profile(agent, question)
    if method == "anti_stereotype":
        return build_anti_stereotype(agent, question)
    if method == "full_history":
        return build_full_history(agent, question, config.full_history_char_budget)
    if method == "random_event":
        return build_retrieval(agent, question, retrieved)
    if method == "event_rag":
        return build_retrieval(agent, question, retrieved)
    if method == "lifemem_no_struct":
        return build_profile(agent, question)
    return build_retrieval(agent, question, retrieved)


def run_method(
    method: str,
    panel: Panel,
    config: LifeMemConfig,
    respondent: Any | None = None,
) -> list[GenerationRecord]:
    rng = Random(config.seed + sum(ord(ch) for ch in method))
    encoder = HashedEventEncoder(dim=config.hashed_dim)
    if respondent is None:
        respondent = HeuristicRespondent(seed=config.seed)
    agents = [AgentState(profile=deepcopy(agent.profile)) for agent in panel.agents]
    records: list[GenerationRecord] = []
    train_adapter = getattr(respondent, "train_adapter", None)
    generate_batch = getattr(respondent, "generate_batch", None)
    for wave in panel.waves:
        for agent in agents:
            new_events = panel.events_by_wave[(agent.profile.agent_id, wave)]
            replay = _sample_replay(agent.events, config.replay_size, rng)
            if _uses_param(method):
                update_parametric(agent, new_events, replay, encoder)
                if train_adapter is not None:
                    train_adapter(method, agent, new_events, replay)
            agent.events.extend(new_events)
        for agent in agents:
            packed: list[tuple[SurveyQuestion, list[RetrievedEvent], str]] = []
            for question in panel.questions:
                if method == "random_event":
                    retrieved = [
                        RetrievedEvent(
                            event=event,
                            semantic_similarity=0.0,
                            recency_weight=1.0,
                            final_score=0.0,
                        )
                        for event in _other_events(
                            panel, agent.profile.agent_id, wave, config.top_k, rng
                        )
                    ]
                elif _uses_struct(method) or method == "event_rag":
                    retrieved = retrieve_events(
                        query=question,
                        events=agent.events,
                        current_wave=wave,
                        top_k=config.top_k,
                        alpha=config.forgetting_alpha,
                        encoder=encoder,
                    )
                else:
                    retrieved = []
                packed.append(
                    (
                        question,
                        retrieved,
                        build_prompt(method, agent, question, retrieved, config),
                    )
                )
            if generate_batch is not None:
                raws = generate_batch(
                    [row[2] for row in packed],
                    questions=[row[0] for row in packed],
                    agent=agent,
                    retrieved_lists=[row[1] for row in packed],
                    use_parametric=_uses_param(method),
                    method=method,
                )
            else:
                raws = [
                    respondent.generate(
                        prompt=prompt,
                        question=question,
                        agent=agent,
                        retrieved=retrieved,
                        use_parametric=_uses_param(method),
                        method=method,
                    )
                    for question, retrieved, prompt in packed
                ]
            for (question, retrieved, prompt), raw in zip(packed, raws, strict=True):
                text = str(raw)
                parsed = parse_generation(text, question)
                records.append(
                    GenerationRecord(
                        agent_id=agent.profile.agent_id,
                        wave=wave,
                        variable=question.variable,
                        human_answer=panel.humans[
                            (agent.profile.agent_id, wave, question.variable)
                        ],
                        parsed_answer=parsed,
                        valid_options=question.option_codes,
                        method=method,
                        identity_groups=_identity(agent),
                        retrieved_event_ids=tuple(
                            item.event.event_id for item in retrieved
                        ),
                        prompt=prompt,
                        raw_output=text,
                        valid=bool(parsed and parsed in question.option_codes),
                    )
                )
    return records


def adapter_pca(panel: Panel, config: LifeMemConfig) -> dict[str, Any]:
    encoder = HashedEventEncoder(dim=config.hashed_dim)
    traces: list[dict[str, Any]] = []
    for agent_template in panel.agents:
        agent = AgentState(profile=deepcopy(agent_template.profile))
        for wave in panel.waves:
            events = panel.events_by_wave[(agent.profile.agent_id, wave)]
            replay = _sample_replay(
                agent.events, config.replay_size, Random(config.seed)
            )
            update_parametric(agent, events, replay, encoder)
            agent.events.extend(events)
            traces.append(
                {
                    "agent_id": agent.profile.agent_id,
                    "ses": agent.profile.ses,
                    "wave": wave,
                    "vector": list(agent.adapter_vector),
                }
            )
    matrix = np.asarray([row["vector"] for row in traces], dtype=np.float64)
    coords = pca_2d(matrix)
    for row, coord in zip(traces, coords, strict=True):
        row["x"] = float(coord[0])
        row["y"] = float(coord[1])
        del row["vector"]
    return {"points": traces}


def identity_pca(records: list[GenerationRecord], field: str) -> dict[str, Any]:
    matrix, agent_ids, groups = response_matrix(records, field)
    coords = pca_2d(matrix)
    score = silhouette(matrix, groups) if matrix.size else 0.0
    return {
        "silhouette": score,
        "points": [
            {"agent_id": agent_id, "ses": group, "x": float(xy[0]), "y": float(xy[1])}
            for agent_id, group, xy in zip(agent_ids, groups, coords, strict=True)
        ],
    }


def run_suite(
    config: LifeMemConfig | None = None,
    n_agents: int = 24,
    n_waves: int = 6,
    events_per_wave: int = 8,
    backend: str = "heuristic",
    respondent: Any | None = None,
) -> dict[str, Any]:
    config = config or LifeMemConfig()
    panel = build_panel(
        n_agents=n_agents,
        n_waves=n_waves,
        events_per_wave=events_per_wave,
        seed=config.seed,
    )
    if respondent is None:
        respondent = _make_respondent(backend, config)
    method_records: dict[str, list[GenerationRecord]] = {}
    summaries: dict[str, Any] = {}
    for method in config.methods:
        records = run_method(method, panel, config, respondent=respondent)
        method_records[method] = records
        summaries[method] = summarize_method(records, config.group_variables)
    last_wave = panel.waves[-1]

    def _last(method: str) -> list[GenerationRecord]:
        return [row for row in method_records.get(method, []) if row.wave == last_wave]

    identity: dict[str, Any] = {}
    if "profile" in method_records:
        identity["human"] = identity_pca(_last("profile"), "human_answer")
        identity["profile"] = identity_pca(_last("profile"), "parsed_answer")
    if "lifemem" in method_records:
        identity["lifemem"] = identity_pca(_last("lifemem"), "parsed_answer")
    if "direct" in method_records:
        identity["direct"] = identity_pca(_last("direct"), "parsed_answer")

    return {
        "config": {
            "seed": config.seed,
            "n_agents": n_agents,
            "n_waves": n_waves,
            "events_per_wave": events_per_wave,
            "model": config.model_name,
            "backend": backend,
            "top_k": config.top_k,
            "forgetting_alpha": config.forgetting_alpha,
        },
        "methods": summaries,
        "identity": identity,
        "adapter_pca": adapter_pca(panel, config),
        "examples": _examples(method_records, panel),
    }


def _examples(
    method_records: dict[str, list[GenerationRecord]], panel: Panel
) -> list[dict[str, Any]]:
    sample_agent = panel.agents[0].profile.agent_id
    question = panel.questions[2]
    last = panel.waves[-1]
    rows = []
    for method, records in method_records.items():
        match = next(
            row
            for row in records
            if row.agent_id == sample_agent
            and row.wave == last
            and row.variable == question.variable
        )
        rows.append(
            {
                "method": method,
                "agent_id": sample_agent,
                "wave": last,
                "variable": question.variable,
                "question": question.question,
                "human": match.human_answer,
                "model": match.parsed_answer,
                "retrieved_event_ids": list(match.retrieved_event_ids),
                "prompt": match.prompt,
            }
        )
    return rows


def _make_respondent(backend: str, config: LifeMemConfig) -> Any:
    if backend in {"llm", "qwen", "gpu"}:
        from lifemem.llm import QwenRespondent

        return QwenRespondent(config)
    return HeuristicRespondent(seed=config.seed)


def write_json(data: dict[str, Any], path: Path) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=_json_default), encoding="utf-8")


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
