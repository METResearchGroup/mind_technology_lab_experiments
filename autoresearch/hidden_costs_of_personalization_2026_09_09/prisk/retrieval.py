"""Query-only routing and bag-of-words memory retrieval (k=3)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from prisk.schemas import MemoryConversation, SeedCase, Setting

_TOKEN = re.compile(r"[a-z0-9']+")
_STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "with",
    "you",
}
_RETRIEVE_HINTS = (
    "recommend",
    "advice",
    "plan",
    "should i",
    "what should",
    "best for me",
    "for me",
    "my",
    "i've",
    "ive",
    "lately",
)


@dataclass(frozen=True)
class RetrievedMemory:
    doc_id: str
    score: float
    text: str
    focal_attribute: str


def tokenize(text: str) -> list[str]:
    return [tok for tok in _TOKEN.findall(text.lower()) if tok not in _STOP]


def _tf_vector(text: str) -> dict[str, float]:
    counts: dict[str, float] = {}
    for tok in tokenize(text):
        counts[tok] = counts.get(tok, 0.0) + 1.0
    return counts


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0.0) for key, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def conversation_text(conversation: MemoryConversation) -> str:
    lines = [f"Prior conversation focused on {conversation.focal_attribute}."]
    for turn in conversation.turns:
        lines.append(f"{turn.role}: {turn.content}")
    return "\n".join(lines)


def format_memories(memories: list[RetrievedMemory]) -> str:
    if not memories:
        return "No retrieved memories."
    blocks: list[str] = []
    for index, memory in enumerate(memories, start=1):
        blocks.append(f"[Memory {index}] score={memory.score:.4f}")
        blocks.append(memory.text)
    return "\n".join(blocks)


def route_query(text: str, risk_type: str | None = None) -> dict[str, str]:
    """Keyword router used when no LLM router is available.

    Factual IRP items stay on the no-retrieval path. Advice and moral-judgment
    queries retrieve, matching the paper's observation that identity-independent
    questions rarely pull memory.
    """
    if risk_type in {"preference_narrowing", "sycophantic_bias"}:
        return {
            "decision": "retrieval",
            "reason": "Personalization-sensitive query family.",
        }
    lowered = text.lower()
    if any(hint in lowered for hint in _RETRIEVE_HINTS):
        return {"decision": "retrieval", "reason": "Advice or first-person cue."}
    return {"decision": "no_retrieval", "reason": "Query looks identity-independent."}


def retrieve_memories(
    query: str,
    case: SeedCase,
    top_k: int = 3,
) -> list[RetrievedMemory]:
    query_vec = _tf_vector(query)
    scored: list[RetrievedMemory] = []
    for index, conversation in enumerate(case.memories):
        text = conversation_text(conversation)
        score = cosine_similarity(query_vec, _tf_vector(text))
        scored.append(
            RetrievedMemory(
                doc_id=f"{case.profile.persona_id}_h{index:02d}",
                score=round(score, 6),
                text=text,
                focal_attribute=conversation.focal_attribute,
            )
        )
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]


def memories_for_setting(
    case: SeedCase,
    setting: Setting,
    top_k: int = 3,
) -> tuple[str | None, list[RetrievedMemory]]:
    if setting not in {"retrieval_only", "profile_retrieval"}:
        return None, []
    routing_query = (
        f"{case.personalization_prompt}\n{case.question}"
        if setting == "profile_retrieval"
        else case.question
    )
    routed = route_query(routing_query, risk_type=case.risk_type)
    if routed["decision"] != "retrieval":
        return routed["decision"], []
    return routed["decision"], retrieve_memories(routing_query, case, top_k=top_k)
