from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SurveyOption:
    code: str
    text: str


@dataclass(frozen=True)
class SurveyQuestion:
    variable: str
    section: str
    question: str
    options: tuple[SurveyOption, ...]
    kind: str = "evaluate"

    @property
    def option_codes(self) -> tuple[str, ...]:
        return tuple(option.code for option in self.options)


@dataclass
class LifeEvent:
    event_id: str
    agent_id: str
    wave: int
    section: str
    question: str
    answer_code: str
    answer_text: str
    statement: str
    first_person: str
    tags: tuple[str, ...] = ()

    def retrieval_text(self) -> str:
        return (
            f"Wave {self.wave}. Section: {self.section}. "
            f"Question: {self.question} Answer: {self.answer_text}. "
            f"Statement: {self.statement}"
        )


@dataclass(frozen=True)
class RetrievedEvent:
    event: LifeEvent
    semantic_similarity: float
    recency_weight: float
    final_score: float


@dataclass
class AgentProfile:
    agent_id: str
    sex: str
    ses: str
    education: str
    religion: str
    region: str
    birth_year: int
    occupation: str
    latent: tuple[float, ...]
    profile_text: str


@dataclass
class AgentState:
    profile: AgentProfile
    events: list[LifeEvent] = field(default_factory=list)
    parametric: dict[str, str] = field(default_factory=dict)
    adapter_vector: list[float] = field(default_factory=list)
    adapter_trace: list[list[float]] = field(default_factory=list)


@dataclass
class GenerationRecord:
    agent_id: str
    wave: int
    variable: str
    human_answer: str
    parsed_answer: str | None
    valid_options: tuple[str, ...]
    method: str
    identity_groups: dict[str, str]
    retrieved_event_ids: tuple[str, ...] = ()
    prompt: str = ""
    raw_output: str = ""
    valid: bool = True
