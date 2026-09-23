"""Typed records for the PRISK factorial evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RiskType = Literal[
    "irrelevant_personalization",
    "preference_narrowing",
    "sycophantic_bias",
]
Setting = Literal["base", "profile_only", "retrieval_only", "profile_retrieval"]
SETTINGS: tuple[Setting, ...] = (
    "base",
    "profile_only",
    "retrieval_only",
    "profile_retrieval",
)


@dataclass(frozen=True)
class MemoryTurn:
    role: str
    content: str


@dataclass(frozen=True)
class MemoryConversation:
    focal_attribute: str
    turns: tuple[MemoryTurn, ...]


@dataclass(frozen=True)
class UserProfile:
    persona_id: str
    persona: str
    attributes: dict[str, str]
    preferences: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedCase:
    record_id: str
    risk_type: RiskType
    domain: str
    question: str
    gold_answer: str | None
    profile: UserProfile
    personalization_prompt: str
    memories: tuple[MemoryConversation, ...]
    universal_answers: tuple[str, ...] = ()
    useful_answers: tuple[str, ...] = ()
    user_is_at_fault: bool = False
    stated_preference: str | None = None


@dataclass
class GenerationResult:
    record_id: str
    risk_type: RiskType
    setting: Setting
    question: str
    prompt: str
    response: str
    backend: str
    model_name: str
    router_decision: str | None = None
    retrieved_memories: list[str] = field(default_factory=list)


@dataclass
class ScoredResult:
    generation: GenerationResult
    irp_score: float | None = None
    uir: float | None = None
    coverage_rate: float | None = None
    relative_coverage: float | None = None
    syco_score: float | None = None
    pis_score: float | None = None
    covered_answers: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
