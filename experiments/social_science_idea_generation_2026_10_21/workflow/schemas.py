# ruff: noqa: E501
"""Pydantic records for rounds, ballots, and the study result.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "from workflow.schemas import StudyResult; print(StudyResult.__name__)"
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class ResearchIdea(BaseModel):
    """One research idea from a seed or synthesis turn."""

    title: str
    question: str
    claim: str
    population: str
    outcome: str
    why_it_might_be_nonobvious: str


class Comment(BaseModel):
    """One objection and one alternative from a comment turn."""

    objection: str
    alternative: str


class MethodPlan(BaseModel):
    """The first method pass for a synthesized idea."""

    design: str
    data: str
    comparison: str
    main_threat: str


class Critique(BaseModel):
    """Flaws the revision has to answer."""

    fatal: bool
    flaws: list[str]
    required_change: str


class RevisedProposal(BaseModel):
    """The idea and method after the critique."""

    idea: ResearchIdea
    method: MethodPlan
    what_changed: str


class CriterionScore(BaseModel):
    """Scores for one revised proposal. Each score is an integer from 1 to 5."""

    round_index: int = Field(ge=1, le=5)
    non_obvious: int = Field(ge=1, le=5)
    feasible: int = Field(ge=1, le=5)
    method_fits_question: int = Field(ge=1, le=5)


class Ballot(BaseModel):
    """One voter's five scores and the token counts from that call."""

    voter: str
    scores: list[CriterionScore] = Field(min_length=5, max_length=5)
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int


class TurnKind(StrEnum):
    """The stage a turn belongs to."""

    SEED = "seed"
    COMMENT = "comment"
    SYNTHESIS = "synthesis"
    METHOD = "method"
    CRITIQUE = "critique"
    REVISION = "revision"
    BALLOT = "ballot"


class TurnRecord(BaseModel):
    """One model call and the structured payload it returned."""

    role: str
    kind: TurnKind
    iteration: int
    payload: dict[str, object]
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_ms: int


class RoundRecord(BaseModel):
    """Every turn in one round, in execution order."""

    round_index: int
    seed_role: str
    thread_id: str
    brief_sha256: str
    turns: list[TurnRecord]


class VoteRecord(BaseModel):
    """Seven ballots and the ranking computed from them."""

    thread_id: str
    ballots: list[Ballot]
    ranking: list[int]
    top_three: list[int]


class StudyResult(BaseModel):
    """The five rounds, the vote, and the token totals for one run."""

    run_id: str
    model_id: str
    reasoning_effort: str
    brief_sha256: str
    rounds: list[RoundRecord]
    vote: VoteRecord
    total_input_tokens: int
    total_output_tokens: int
