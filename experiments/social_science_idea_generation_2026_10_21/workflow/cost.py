# ruff: noqa: E501
"""Token and dollar estimates for a full five-round study plus voting.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "import workflow.cost; print(workflow.cost.CostEstimate.__name__)"
"""

import json
from pathlib import Path

import tiktoken
from pydantic import BaseModel

from workflow.constants import (
    INPUT_USD_PER_MILLION,
    OUTPUT_USD_PER_MILLION,
    PRICE_PAGE_URL,
)
from workflow.prompts import load_prompt
from workflow.schemas import RevisedProposal, RoundRecord, TurnKind

ROUNDS_IN_FULL_RUN = 5
BALLOT_VOTERS = 7
LONG_CONTEXT_INPUT_TOKEN_THRESHOLD = 272_000

_BRIEF_PATH = Path(__file__).resolve().parents[1] / "inputs" / "brief.md"
_ENCODING = tiktoken.get_encoding("o200k_base")


class CostEstimate(BaseModel):
    """Projected token use and cost for five rounds and seven ballots."""

    full_input_tokens: int
    full_output_tokens: int
    estimated_cost_usd: float
    price_page_url: str
    note: str


def _format_revised_proposals(proposals: list[tuple[int, RevisedProposal]]) -> str:
    blocks = [
        f"Round {round_index}\n{json.dumps(proposal.model_dump(), indent=2)}"
        for round_index, proposal in proposals
    ]
    return "\n\n".join(blocks)


def render_ballot_prompt(
    *,
    voter_display_name: str,
    voter_role_id: str,
    brief: str,
    proposals: list[tuple[int, RevisedProposal]],
) -> str:
    """Fill ``templates/ballot.md``. Count this string only, not the persona system prompt.

    Parameters
    ----------
    voter_display_name
        Shown in the ballot header.
    voter_role_id
        Machine id for the voter role.
    brief
        Research brief text.
    proposals
        ``(round_index, proposal)`` pairs to embed.

    Returns
    -------
    str
        Rendered ballot user message.

    Raises
    ------
    ValueError
        When any template placeholder remains.
    """
    text = load_prompt("templates/ballot.md")
    revised = _format_revised_proposals(proposals)
    text = text.replace("{{voter_display_name}}", voter_display_name)
    text = text.replace("{{voter_role_id}}", voter_role_id)
    text = text.replace("{{brief}}", brief)
    text = text.replace("{{revised_proposals}}", revised)
    if "{{" in text:
        raise ValueError("ballot prompt still contains unreplaced placeholders")
    return text


def _smoke_token_totals(round_record: RoundRecord) -> tuple[int, int]:
    smoke_input = sum(turn.input_tokens for turn in round_record.turns)
    smoke_output = sum(turn.output_tokens for turn in round_record.turns)
    return smoke_input, smoke_output


def _revision_output_tokens(round_record: RoundRecord) -> int:
    revision_turns = [
        turn for turn in round_record.turns if turn.kind == TurnKind.REVISION
    ]
    if len(revision_turns) != 1:
        raise ValueError("expected exactly one revision turn in the smoke round")
    return revision_turns[0].output_tokens


def _load_brief_text() -> str:
    return _BRIEF_PATH.read_text(encoding="utf-8")


def _build_cost_note() -> str:
    threshold = LONG_CONTEXT_INPUT_TOKEN_THRESHOLD
    return (
        "Estimated from the smoke round (round 1), not measured across five rounds. "
        f"A prompt over {threshold} input tokens uses the long-context schedule "
        "(2x input and 1.5x output for the whole request). "
        "This formula stays on the short-context rates and does not switch schedules."
    )


def estimate_full_run_cost(round_record: RoundRecord) -> CostEstimate:
    """Project input, output, and USD for five rounds and seven ballot calls.

    Parameters
    ----------
    round_record
        Measured turns from round 1 (smoke).

    Returns
    -------
    CostEstimate
        Scaled token totals and short-context dollar estimate.

    Raises
    ------
    ValueError
        When the brief hash mismatches or revision turn count is wrong.
    """
    from src.run_round import brief_sha256, revised_proposal

    brief = _load_brief_text()
    if brief_sha256(brief) != round_record.brief_sha256:
        raise ValueError("brief text does not match round_record.brief_sha256")

    smoke_input, smoke_output = _smoke_token_totals(round_record)
    revision_output = _revision_output_tokens(round_record)
    proposal = revised_proposal(round_record)
    labeled = [(index, proposal) for index in range(1, ROUNDS_IN_FULL_RUN + 1)]
    prompt = render_ballot_prompt(
        voter_display_name="Social psychologist",
        voter_role_id="social_psychologist",
        brief=brief,
        proposals=labeled,
    )
    tokens_per_ballot = len(_ENCODING.encode(prompt))
    ballot_input = BALLOT_VOTERS * tokens_per_ballot
    full_input = ROUNDS_IN_FULL_RUN * smoke_input + ballot_input
    full_output = ROUNDS_IN_FULL_RUN * smoke_output + BALLOT_VOTERS * revision_output
    estimated_cost_usd = (
        full_input / 1_000_000 * INPUT_USD_PER_MILLION
        + full_output / 1_000_000 * OUTPUT_USD_PER_MILLION
    )
    return CostEstimate(
        full_input_tokens=full_input,
        full_output_tokens=full_output,
        estimated_cost_usd=estimated_cost_usd,
        price_page_url=PRICE_PAGE_URL,
        note=_build_cost_note(),
    )
