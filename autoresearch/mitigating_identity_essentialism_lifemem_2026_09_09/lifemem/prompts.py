from __future__ import annotations

from lifemem.statements import option_block
from lifemem.types import AgentState, RetrievedEvent, SurveyQuestion

ROLEPLAY = (
    "You are not an AI assistant; you are role-playing a human survey respondent. "
    "Answer as that person."
)
ANTI_STEREOTYPE = (
    "Do not assume that one demographic attribute determines another. "
    "When information is missing, preserve uncertainty rather than filling it with stereotypes."
)


def _join(*blocks: str) -> str:
    return "\n\n".join(block for block in blocks if block)


def build_direct(question: SurveyQuestion) -> str:
    return _join(
        ROLEPLAY,
        "Simulate one person and answer the following question.",
        option_block(question),
    )


def build_profile(agent: AgentState, question: SurveyQuestion, extra: str = "") -> str:
    return _join(
        ROLEPLAY,
        "You are answering a longitudinal social survey as the described person.",
        f"Demographic profile:\n{agent.profile.profile_text}",
        extra,
        option_block(question),
    )


def build_anti_stereotype(agent: AgentState, question: SurveyQuestion) -> str:
    return build_profile(agent, question, extra=ANTI_STEREOTYPE)


def build_retrieval(
    agent: AgentState,
    question: SurveyQuestion,
    retrieved: list[RetrievedEvent],
    include_profile: bool = True,
) -> str:
    profile = (
        agent.profile.profile_text
        if include_profile
        else "Profile omitted by ablation."
    )
    if retrieved:
        events = "\n".join(f"- {item.event.statement}" for item in retrieved)
    else:
        events = "No relevant life experiences retrieved."
    return _join(
        ROLEPLAY,
        "You are answering a longitudinal social survey as the described person.",
        f"Demographic profile:\n{profile}",
        f"Relevant life experiences:\n{events}",
        option_block(question),
    )


def build_full_history(
    agent: AgentState,
    question: SurveyQuestion,
    max_chars: int,
) -> str:
    lines = [f"- {event.statement}" for event in agent.events]
    kept: list[str] = []
    total = 0
    for line in reversed(lines):
        if total + len(line) > max_chars:
            continue
        kept.append(line)
        total += len(line)
    event_block = "\n".join(reversed(kept)) if kept else "No life events available."
    return _join(
        ROLEPLAY,
        "You are answering a longitudinal social survey as the described person.",
        f"Demographic profile:\n{agent.profile.profile_text}",
        f"Life history:\n{event_block}",
        option_block(question),
    )
