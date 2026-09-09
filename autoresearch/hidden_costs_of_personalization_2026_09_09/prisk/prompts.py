"""Prompt construction for the four PRISK inference settings."""

from __future__ import annotations

from prisk.retrieval import RetrievedMemory, format_memories
from prisk.schemas import SeedCase, Setting


def build_user_prompt(
    case: SeedCase,
    setting: Setting,
    memories: list[RetrievedMemory] | None = None,
) -> str:
    """Build the user message injected with the selected personalization context."""
    question = case.question
    if setting == "base":
        return question
    if setting == "profile_only":
        return f"{case.personalization_prompt}\n{question}"
    formatted = format_memories(memories or [])
    if setting == "retrieval_only":
        if not memories:
            return question
        return f"Retrieved user memory:\n{formatted}\n\n{question}"
    if memories:
        return (
            f"Retrieved user memory:\n{formatted}\n\n"
            f"{case.personalization_prompt}\n{question}"
        )
    return f"{case.personalization_prompt}\n{question}"


def system_prompt(setting: Setting) -> str:
    if setting in {"profile_only", "profile_retrieval"}:
        return "You are a helpful, personalized assistant."
    return "You are a helpful assistant."
