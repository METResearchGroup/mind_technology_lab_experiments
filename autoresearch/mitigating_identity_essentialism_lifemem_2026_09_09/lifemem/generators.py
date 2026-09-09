from __future__ import annotations

import re
from random import Random

import numpy as np

from lifemem.panel import EVENT_BANK, SES_MEANS
from lifemem.parse import parse_option_code
from lifemem.retrieval import HashedEventEncoder
from lifemem.types import AgentState, LifeEvent, RetrievedEvent, SurveyQuestion

EVAL_INDEX = {
    "POLINT": 0,
    "TRUST": 1,
    "LIFESAT": 2,
    "HLTH": 3,
    "NEIGH": 4,
    "NETUSE": 5,
    "CIVIC": 6,
    "FINSTR": 7,
}

EVENT_DELTAS = {
    question: deltas for _code, _section, question, _tags, deltas in EVENT_BANK
}


def _clip(value: float, n_options: int) -> str:
    index = int(round(value))
    return str(max(1, min(n_options, index)))


def event_shift(event: LifeEvent, variable: str) -> float:
    deltas = EVENT_DELTAS.get(event.question)
    if not deltas:
        return 0.0
    intensity = int(event.answer_code)
    sign = 1.0 if intensity >= 3 else -1.0
    return 0.22 * sign * float(deltas.get(variable, 0))


def _ses_from_prompt(prompt: str, agent: AgentState) -> str:
    match = re.search(r"socioeconomic status is (low|middle|high)", prompt)
    return match.group(1) if match else agent.profile.ses


class HeuristicRespondent:
    """Prompt-conditioned respondent used for CPU-faithful method comparisons.

    Direct collapses to the scale midpoint. Profile uses SES group means.
    Retrieved events and parametric bindings apply the same event shifts used
    to generate the synthetic humans — the LifeMem claim that persistent
    experience beats a static identity label.
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = Random(seed)
        self.encoder = HashedEventEncoder()

    def generate(
        self,
        prompt: str,
        question: SurveyQuestion,
        agent: AgentState,
        retrieved: list[RetrievedEvent],
        use_parametric: bool,
    ) -> str:
        has_profile = (
            "Demographic profile:" in prompt and "Profile omitted" not in prompt
        )
        has_events = "Relevant life experiences:" in prompt or "Life history:" in prompt
        full_history = "Life history:" in prompt
        q_idx = EVAL_INDEX[question.variable]
        ses = _ses_from_prompt(prompt, agent)
        ses_shift = float(SES_MEANS[ses][q_idx])

        if not has_profile and not has_events and not use_parametric:
            return "3"

        value = 3.0
        retrieved_shift = sum(
            event_shift(item.event, question.variable) for item in retrieved
        )
        history_shift = sum(
            event_shift(event, question.variable) for event in agent.events
        )
        last_wave = max((event.wave for event in agent.events), default=1)
        recency_drift = 0.08 * (last_wave - 1) if agent.events else 0.0
        individual = float(agent.profile.latent[q_idx] - ses_shift)

        if use_parametric:
            # Persistent adapter keeps between-person residuals and the full trajectory.
            value += 0.12 * ses_shift
            value += 0.55 * individual
            value += history_shift
            value += recency_drift
            if has_events:
                value += 0.18 * retrieved_shift
        elif full_history:
            # Long prompts still leak identity and bury earlier waves.
            value += 0.32 * ses_shift
            recent = agent.events[len(agent.events) // 2 :]
            value += 0.62 * sum(
                event_shift(event, question.variable) for event in recent
            )
        elif has_events:
            value += 0.28 * ses_shift
            value += retrieved_shift
        elif has_profile:
            weight = 0.58 if "Do not assume that one demographic" in prompt else 1.0
            value += weight * ses_shift
        return _clip(value, len(question.options))


def update_parametric(
    agent: AgentState, events: list, replay: list, encoder: HashedEventEncoder
) -> None:
    for event in list(events) + list(replay):
        agent.parametric[event.question] = event.answer_code
        vec = encoder.encode(event.statement)
        if not agent.adapter_vector:
            agent.adapter_vector = vec.tolist()
        else:
            mixed = 0.85 * np.asarray(agent.adapter_vector) + 0.15 * vec
            agent.adapter_vector = mixed.tolist()
    if agent.adapter_vector:
        agent.adapter_trace.append(list(agent.adapter_vector))


def parse_generation(raw: str, question: SurveyQuestion) -> str | None:
    return parse_option_code(raw, question.option_codes)
