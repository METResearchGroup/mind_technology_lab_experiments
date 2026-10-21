# ruff: noqa: E501
"""Run five discussion rounds, a seven-voter ballot, and persist study artifacts.

Blocked command (do not run until a human accepts the smoke cost):

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -m src.run_study
"""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_openai import ChatOpenAI
from langsmith import uuid7
from pydantic import BaseModel, Field
from workflow.agents import build_chat_model
from workflow.constants import (
    EXPERIMENT_NAME,
    MODEL_ID,
    REASONING_EFFORT,
    S3_BUCKET,
)
from workflow.cost import render_ballot_prompt
from workflow.roles import CRITIC, METHODOLOGIST, ROLE_ORDER, RoleSpec
from workflow.schemas import (
    Ballot,
    CriterionScore,
    RevisedProposal,
    RoundRecord,
    StudyResult,
    TurnKind,
    TurnRecord,
    VoteRecord,
)
from workflow.tracing import configure_tracing

from lib.load_env_vars import EnvVarsContainer
from shared.aws.constants import DEFAULT_REGION_NAME
from shared.aws.s3 import S3
from src.run_round import (
    brief_sha256,
    revised_proposal,
    run_round,
    run_turn,
)

VOTERS: tuple[RoleSpec, ...] = (*ROLE_ORDER, METHODOLOGIST, CRITIC)


class BallotScores(BaseModel):
    """Model-facing scores. Token fields stay on Ballot, filled by the driver."""

    scores: list[CriterionScore] = Field(min_length=5, max_length=5)


def _experiment_root() -> Path:
    """Return the experiment directory (parent of ``src``)."""
    return Path(__file__).resolve().parents[1]


def _require_run_id(run_id: str) -> None:
    """Raise when ``run_id`` is empty."""
    if not run_id:
        raise ValueError("run_id must be non-empty")


def _score_total(score: CriterionScore) -> int:
    """Sum the three criterion scores for one proposal on one ballot."""
    return score.non_obvious + score.feasible + score.method_fits_question


def _expected_round_indexes(rounds: list[RoundRecord]) -> set[int]:
    """Round indexes that every ballot must score."""
    return {record.round_index for record in rounds}


def _validate_ballot_scores(ballot: Ballot, expected: set[int]) -> None:
    """Ensure the ballot has exactly one score row per round index."""
    found = {score.round_index for score in ballot.scores}
    if found != expected:
        raise ValueError(f"ballot from {ballot.voter} missing score rows")


def _round_means(ballots: list[Ballot], round_index: int) -> tuple[float, float]:
    """Return mean total and mean feasible for one round across ballots."""
    totals: list[int] = []
    feasibles: list[int] = []
    for ballot in ballots:
        for score in ballot.scores:
            if score.round_index == round_index:
                totals.append(_score_total(score))
                feasibles.append(score.feasible)
    count = len(totals)
    return sum(totals) / count, sum(feasibles) / count


def _compute_ranking(ballots: list[Ballot], round_indexes: list[int]) -> list[int]:
    """Sort round indexes by mean ballot total, then feasible, then index."""
    keys: list[tuple[float, float, int]] = []
    for round_index in round_indexes:
        mean_total, mean_feasible = _round_means(ballots, round_index)
        keys.append((mean_total, mean_feasible, round_index))
    keys.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [item[2] for item in keys]


def _ballot_from_turn(
    voter: RoleSpec,
    turn: TurnRecord,
    expected: set[int],
) -> Ballot:
    """Build a ``Ballot`` from one ballot turn and validate score rows."""
    parsed = BallotScores.model_validate(turn.payload)
    ballot = Ballot(
        voter=voter.role_id,
        scores=parsed.scores,
        input_tokens=turn.input_tokens,
        output_tokens=turn.output_tokens,
        reasoning_tokens=turn.reasoning_tokens,
    )
    _validate_ballot_scores(ballot, expected)
    return ballot


def _cast_ballot(
    voter: RoleSpec,
    brief: str,
    proposals: list[tuple[int, RevisedProposal]],
    thread_id: str,
    chat_model: ChatOpenAI,
    expected: set[int],
) -> Ballot:
    """Run one ballot turn and return a validated ``Ballot``."""
    transcript = render_ballot_prompt(
        voter_display_name=voter.display_name,
        voter_role_id=voter.role_id,
        brief=brief,
        proposals=proposals,
    )
    turn = run_turn(
        voter,
        TurnKind.BALLOT,
        BallotScores,
        transcript,
        thread_id,
        chat_model,
    )
    return _ballot_from_turn(voter, turn, expected)


def run_vote(
    rounds: list[RoundRecord],
    run_id: str,
    brief: str,
    chat_model: ChatOpenAI,
) -> VoteRecord:
    """Collect seven ballots on one thread; return ranking and top three."""
    _require_run_id(run_id)
    thread_id = str(uuid7())
    proposals = [(record.round_index, revised_proposal(record)) for record in rounds]
    expected = _expected_round_indexes(rounds)
    ballots = [
        _cast_ballot(voter, brief, proposals, thread_id, chat_model, expected)
        for voter in VOTERS
    ]
    round_indexes = [record.round_index for record in rounds]
    ranking = _compute_ranking(ballots, round_indexes)
    return VoteRecord(
        thread_id=thread_id,
        ballots=ballots,
        ranking=ranking,
        top_three=ranking[:3],
    )


def _sum_turn_tokens(rounds: list[RoundRecord]) -> tuple[int, int]:
    """Sum input and output tokens from all round turns."""
    input_tokens = 0
    output_tokens = 0
    for record in rounds:
        for turn in record.turns:
            input_tokens += turn.input_tokens
            output_tokens += turn.output_tokens
    return input_tokens, output_tokens


def _sum_ballot_tokens(ballots: list[Ballot]) -> tuple[int, int]:
    """Sum input and output tokens from all ballots."""
    input_tokens = sum(ballot.input_tokens for ballot in ballots)
    output_tokens = sum(ballot.output_tokens for ballot in ballots)
    return input_tokens, output_tokens


def _token_totals(rounds: list[RoundRecord], vote: VoteRecord) -> tuple[int, int]:
    """Combine turn and ballot token counts (excluding reasoning)."""
    turn_in, turn_out = _sum_turn_tokens(rounds)
    ballot_in, ballot_out = _sum_ballot_tokens(vote.ballots)
    return turn_in + ballot_in, turn_out + ballot_out


def _run_dir(run_id: str) -> Path:
    """Local output directory for one study run."""
    return _experiment_root() / "outputs" / "runs" / run_id


def _s3_run_prefix(run_id: str) -> str:
    """S3 key prefix for one study run."""
    return f"experiments/{EXPERIMENT_NAME}/runs/{run_id}"


def _write_study_json(path: Path, result: StudyResult) -> None:
    """Write ``study.json`` for one run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def _proposal_section(rounds: list[RoundRecord], round_index: int) -> str:
    """Markdown block for one top proposal."""
    proposal = revised_proposal(
        next(record for record in rounds if record.round_index == round_index)
    )
    return (
        f"### Round {round_index}\n\n"
        f"- **Title:** {proposal.idea.title}\n"
        f"- **Question:** {proposal.idea.question}\n"
        f"- **Method design:** {proposal.method.design}\n"
    )


def _format_results_md(result: StudyResult) -> str:
    """Build a short human-readable report for one study."""
    lines = ["# Study results", "", "## Top three proposals", ""]
    for round_index in result.vote.top_three:
        lines.append(_proposal_section(result.rounds, round_index))
        lines.append("")
    lines.extend(["## Round threads", ""])
    for record in result.rounds:
        lines.append(f"- Round {record.round_index}: `{record.thread_id}`")
    lines.append("")
    return "\n".join(lines)


def _write_results_md(path: Path, result: StudyResult) -> None:
    """Write ``RESULTS.md`` for one run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_format_results_md(result), encoding="utf-8")


def _upload_study_artifacts(
    run_id: str,
    study_path: Path,
    results_path: Path,
) -> None:
    """Upload ``study.json`` and ``RESULTS.md`` to S3."""
    prefix = _s3_run_prefix(run_id)
    client = S3(S3_BUCKET, region_name=DEFAULT_REGION_NAME)
    client.upload_file(study_path, f"{prefix}/study.json")
    client.upload_file(results_path, f"{prefix}/RESULTS.md")


def _load_api_keys() -> tuple[str, str]:
    """Load OpenAI and LangSmith keys (never log or print)."""
    openai_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    langsmith_key = EnvVarsContainer.get_env_var("LANGSMITH_API_KEY", required=True)
    return openai_key, langsmith_key


def _assemble_study_result(
    run_id: str,
    brief: str,
    rounds: list[RoundRecord],
    vote: VoteRecord,
) -> StudyResult:
    """Build ``StudyResult`` with token totals from rounds and ballots."""
    total_in, total_out = _token_totals(rounds, vote)
    return StudyResult(
        run_id=run_id,
        model_id=MODEL_ID,
        reasoning_effort=REASONING_EFFORT,
        brief_sha256=brief_sha256(brief),
        rounds=rounds,
        vote=vote,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
    )


def _persist_study_outputs(result: StudyResult, run_id: str) -> None:
    """Write local artifacts and upload ``study.json`` and ``RESULTS.md``."""
    out_dir = _run_dir(run_id)
    study_path = out_dir / "study.json"
    results_path = out_dir / "RESULTS.md"
    _write_study_json(study_path, result)
    _write_results_md(results_path, result)
    _upload_study_artifacts(run_id, study_path, results_path)


def run_study(brief_path: Path, run_id: str) -> StudyResult:
    """Run five rounds, vote, persist ``study.json`` and ``RESULTS.md``, upload S3."""
    _require_run_id(run_id)
    openai_key, langsmith_key = _load_api_keys()
    configure_tracing(langsmith_key)
    brief = brief_path.read_text(encoding="utf-8")
    chat_model = build_chat_model(openai_key)
    rounds = [run_round(index, brief, run_id) for index in range(1, 6)]
    vote = run_vote(rounds, run_id, brief, chat_model)
    result = _assemble_study_result(run_id, brief, rounds, vote)
    _persist_study_outputs(result, run_id)
    return result


def main() -> None:
    """CLI entry: optional ``run_id`` argument, default brief, print ``run_id`` only."""
    run_id = sys.argv[1] if len(sys.argv) > 1 else str(uuid7())
    brief_path = _experiment_root() / "inputs" / "brief.md"
    run_study(brief_path, run_id)
    print(run_id)


if __name__ == "__main__":
    main()
