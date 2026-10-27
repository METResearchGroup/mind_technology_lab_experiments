# ruff: noqa: E501
"""Run one discussion round: seed, comments, synthesis, method, critique, revision.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "from src.run_round import brief_sha256; print(brief_sha256('x')[:8])"
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from typing import Any

from langchain.agents.structured_output import StructuredOutputError
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langsmith import uuid7
from pydantic import BaseModel, ValidationError
from workflow.agents import build_chat_model, build_role_agent
from workflow.constants import DISCUSSION_ITERATIONS
from workflow.prompts import load_prompt
from workflow.roles import (
    CRITIC,
    METHODOLOGIST,
    ROLE_ORDER,
    SYNTHESIZER,
    RoleSpec,
)
from workflow.schemas import (
    Comment,
    Critique,
    MethodPlan,
    ResearchIdea,
    RevisedProposal,
    RoundRecord,
    TurnKind,
    TurnRecord,
)
from workflow.tracing import configure_tracing

from lib.load_env_vars import EnvVarsContainer

INVOKE_ATTEMPTS = 2
PRIOR_COMMENTS_ITERATION_TWO_THRESHOLD = 4
EMPTY_PRIOR_COMMENTS = "none yet"
STRUCTURED_RESPONSE_KEY = "structured_response"


class _TurnInvokeError(Exception):
    """Retryable failure after a graph invoke returned or rejected output."""

    def __init__(
        self,
        message: str,
        usage: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        super().__init__(message)
        self.usage = usage


def brief_sha256(brief: str) -> str:
    """Return the SHA-256 hex digest of the brief UTF-8 bytes.

    Parameters
    ----------
    brief
        Research brief text (not stripped).

    Returns
    -------
    str
        Lowercase hex digest.
    """
    return hashlib.sha256(brief.encode("utf-8")).hexdigest()


def _ensure_filled(text: str) -> str:
    if "{{" in text:
        raise ValueError("prompt still contains unreplaced placeholders")
    return text


def _apply_replacements(text: str, pairs: dict[str, str]) -> str:
    for key, value in pairs.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return _ensure_filled(text)


def _single_turn(turns: list[TurnRecord], kind: TurnKind) -> TurnRecord:
    matches = [turn for turn in turns if turn.kind == kind]
    if len(matches) != 1:
        message = f"expected exactly one {kind.value} turn"
        raise ValueError(message)
    return matches[0]


def _comment_payloads(turns: list[TurnRecord]) -> list[dict[str, object]]:
    return [turn.payload for turn in turns if turn.kind == TurnKind.COMMENT]


def _discussion_json(turns: list[TurnRecord]) -> str:
    rows = [
        {"role": turn.role, "kind": turn.kind.value, "payload": turn.payload}
        for turn in turns
    ]
    return json.dumps(rows, indent=2)


def _transcript_seed(text: str, brief: str, _turns: list[TurnRecord]) -> str:
    return _apply_replacements(text, {"brief": brief})


def _transcript_comment(text: str, brief: str, turns: list[TurnRecord]) -> str:
    prior = _comment_payloads(turns)
    prior_text = json.dumps(prior, indent=2) if prior else EMPTY_PRIOR_COMMENTS
    iteration = "1" if len(prior) < PRIOR_COMMENTS_ITERATION_TWO_THRESHOLD else "2"
    seed_payload = json.dumps(_single_turn(turns, TurnKind.SEED).payload, indent=2)
    pairs = {
        "brief": brief,
        "seed_idea": seed_payload,
        "prior_comments": prior_text,
        "iteration": iteration,
        "discussion_iterations": str(DISCUSSION_ITERATIONS),
    }
    return _apply_replacements(text, pairs)


def _transcript_synthesis(text: str, brief: str, turns: list[TurnRecord]) -> str:
    pairs = {"brief": brief, "discussion": _discussion_json(turns)}
    return _apply_replacements(text, pairs)


def _transcript_method(text: str, brief: str, turns: list[TurnRecord]) -> str:
    idea = json.dumps(_single_turn(turns, TurnKind.SYNTHESIS).payload, indent=2)
    return _apply_replacements(text, {"brief": brief, "idea": idea})


def _transcript_critique(text: str, brief: str, turns: list[TurnRecord]) -> str:
    idea = json.dumps(_single_turn(turns, TurnKind.SYNTHESIS).payload, indent=2)
    method = json.dumps(_single_turn(turns, TurnKind.METHOD).payload, indent=2)
    pairs = {"brief": brief, "idea": idea, "method": method}
    return _apply_replacements(text, pairs)


def _transcript_revision(text: str, brief: str, turns: list[TurnRecord]) -> str:
    idea = json.dumps(_single_turn(turns, TurnKind.SYNTHESIS).payload, indent=2)
    method = json.dumps(_single_turn(turns, TurnKind.METHOD).payload, indent=2)
    critique = json.dumps(_single_turn(turns, TurnKind.CRITIQUE).payload, indent=2)
    pairs = {"brief": brief, "idea": idea, "method": method, "critique": critique}
    return _apply_replacements(text, pairs)


_TRANSCRIPT_BUILDERS: dict[
    TurnKind,
    Callable[[str, str, list[TurnRecord]], str],
] = {
    TurnKind.SEED: _transcript_seed,
    TurnKind.COMMENT: _transcript_comment,
    TurnKind.SYNTHESIS: _transcript_synthesis,
    TurnKind.METHOD: _transcript_method,
    TurnKind.CRITIQUE: _transcript_critique,
    TurnKind.REVISION: _transcript_revision,
}


def transcript_for(kind: TurnKind, brief: str, turns: list[TurnRecord]) -> str:
    """Build the user message for one turn from its template and prior turns.

    Parameters
    ----------
    kind
        Turn stage (not ``TurnKind.BALLOT``).
    brief
        Research brief text.
    turns
        Turns executed so far in this round.

    Returns
    -------
    str
        Filled prompt text.

    Raises
    ------
    ValueError
        For ballot kinds, missing prerequisite turns, or leftover placeholders.
    """
    if kind == TurnKind.BALLOT:
        raise ValueError("ballot transcripts are built in workflow.cost")
    builder = _TRANSCRIPT_BUILDERS.get(kind)
    if builder is None:
        raise ValueError(f"unsupported turn kind: {kind}")
    template = load_prompt(f"templates/{kind.value}.md")
    return builder(template, brief, turns)


def revised_proposal(round_record: RoundRecord) -> RevisedProposal:
    """Return the structured revision from a completed round.

    Parameters
    ----------
    round_record
        Round including exactly one revision turn.

    Returns
    -------
    RevisedProposal
        Parsed revision payload.

    Raises
    ------
    ValueError
        When revision turn count is not one.
    """
    revision_turns = [
        turn for turn in round_record.turns if turn.kind == TurnKind.REVISION
    ]
    if len(revision_turns) != 1:
        raise ValueError("expected exactly one revision turn")
    return RevisedProposal.model_validate(revision_turns[0].payload)


def _messages_from_result(result: dict[str, Any]) -> list[Any]:
    messages = result.get("messages")
    if not isinstance(messages, list):
        raise _TurnInvokeError("invoke result missing messages list")
    return messages


def _has_disallowed_tool_calls(messages: list[Any]) -> bool:
    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            return True
    return False


def _usage_from_message(message: AIMessage) -> tuple[int, int, int]:
    meta = message.usage_metadata or {}
    input_tokens = int(meta.get("input_tokens") or 0)
    output_tokens = int(meta.get("output_tokens") or 0)
    details = meta.get("output_token_details") or {}
    reasoning = int(details.get("reasoning") or 0)
    return input_tokens, output_tokens, reasoning


def _sum_ai_usage(messages: list[Any]) -> tuple[int, int, int]:
    total_in = total_out = total_reason = 0
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        inp, out, reason = _usage_from_message(message)
        total_in += inp
        total_out += out
        total_reason += reason
    return total_in, total_out, total_reason


def _payload_from_result(
    result: dict[str, Any],
    response_model: type[BaseModel],
) -> dict[str, object]:
    raw = result.get(STRUCTURED_RESPONSE_KEY)
    if raw is None:
        raise _TurnInvokeError(f"missing {STRUCTURED_RESPONSE_KEY}")
    if isinstance(raw, response_model):
        return raw.model_dump()
    try:
        return response_model.model_validate(raw).model_dump()
    except ValidationError as exc:
        raise _TurnInvokeError("structured output validation failed") from exc


def _add_usage(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
) -> tuple[int, int, int]:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _parse_invoke_success(
    result: dict[str, Any],
    response_model: type[BaseModel],
) -> tuple[int, int, int, dict[str, object]]:
    messages = _messages_from_result(result)
    usage = _sum_ai_usage(messages)
    if _has_disallowed_tool_calls(messages):
        raise _TurnInvokeError("model returned tool calls", usage)
    try:
        payload = _payload_from_result(result, response_model)
    except _TurnInvokeError as exc:
        raise _TurnInvokeError(str(exc), usage) from exc
    return (*usage, payload)


def _usage_from_output_error(exc: StructuredOutputError) -> tuple[int, int, int]:
    message = getattr(exc, "ai_message", None)
    if isinstance(message, AIMessage):
        return _usage_from_message(message)
    return (0, 0, 0)


def _invoke_once(
    graph: Any,
    transcript: str,
    config: dict[str, dict[str, str]],
    response_model: type[BaseModel],
) -> tuple[int, int, int, dict[str, object]]:
    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=transcript)]},
            config=config,
        )
    except StructuredOutputError as exc:
        usage = _usage_from_output_error(exc)
        raise _TurnInvokeError("structured output rejected", usage) from exc
    return _parse_invoke_success(result, response_model)


def _invoke_config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"metadata": {"thread_id": thread_id}}


def run_turn(
    role: RoleSpec,
    kind: TurnKind,
    response_model: type[BaseModel],
    transcript: str,
    thread_id: str,
    chat_model: ChatOpenAI,
) -> TurnRecord:
    """Run one model call and return a turn record.

    Parameters
    ----------
    role
        Speaker for this turn.
    kind
        Turn stage (stored on the record).
    response_model
        Schema for structured output.
    transcript
        User message text.
    thread_id
        LangSmith thread id for tracing metadata.
    chat_model
        Shared chat model.

    Returns
    -------
    TurnRecord
        Tokens, latency, and validated payload. ``iteration`` is 1.
        Token totals include a failed attempt when the retry succeeds.

    Raises
    ------
    _TurnInvokeError
        Propagates as retry exhaustion after two failed structured parses.
    """
    graph = build_role_agent(role, response_model, chat_model)
    config = _invoke_config(thread_id)
    spent = (0, 0, 0)
    failure: _TurnInvokeError | None = None
    for _attempt in range(INVOKE_ATTEMPTS):
        started = time.perf_counter()
        try:
            inp, out, reason, payload = _invoke_once(
                graph,
                transcript,
                config,
                response_model,
            )
        except _TurnInvokeError as exc:
            spent = _add_usage(spent, exc.usage)
            failure = exc
            continue
        latency_ms = int((time.perf_counter() - started) * 1000)
        total = _add_usage(spent, (inp, out, reason))
        return TurnRecord(
            role=role.role_id,
            kind=kind,
            iteration=1,
            payload=payload,
            input_tokens=total[0],
            output_tokens=total[1],
            reasoning_tokens=total[2],
            latency_ms=latency_ms,
        )
    if failure is None:
        raise _TurnInvokeError("invoke failed")
    raise failure


def _comment_roles_for_seed(seed_role: RoleSpec) -> tuple[RoleSpec, ...]:
    order = ROLE_ORDER
    seed_index = next(
        i for i, role in enumerate(order) if role.role_id == seed_role.role_id
    )
    count = len(order) - 1
    return tuple(
        order[(seed_index + 1 + offset) % len(order)] for offset in range(count)
    )


def _append_turn(
    turns: list[TurnRecord],
    role: RoleSpec,
    kind: TurnKind,
    response_model: type[BaseModel],
    brief: str,
    thread_id: str,
    chat_model: ChatOpenAI,
    comment_pass: int | None = None,
) -> None:
    transcript = transcript_for(kind, brief, turns)
    record = run_turn(role, kind, response_model, transcript, thread_id, chat_model)
    if kind == TurnKind.COMMENT and comment_pass is not None:
        record = record.model_copy(update={"iteration": comment_pass})
    turns.append(record)


def _run_seed_turn(
    turns: list[TurnRecord],
    seed_role: RoleSpec,
    brief: str,
    thread_id: str,
    chat_model: ChatOpenAI,
) -> None:
    _append_turn(
        turns,
        seed_role,
        TurnKind.SEED,
        ResearchIdea,
        brief,
        thread_id,
        chat_model,
    )


def _run_comment_passes(
    turns: list[TurnRecord],
    seed_role: RoleSpec,
    brief: str,
    thread_id: str,
    chat_model: ChatOpenAI,
) -> None:
    roles = _comment_roles_for_seed(seed_role)
    for pass_num in range(1, DISCUSSION_ITERATIONS + 1):
        for role in roles:
            _append_turn(
                turns,
                role,
                TurnKind.COMMENT,
                Comment,
                brief,
                thread_id,
                chat_model,
                comment_pass=pass_num,
            )


_STAFF_SEQUENCE: tuple[tuple[RoleSpec, TurnKind, type[BaseModel]], ...] = (
    (SYNTHESIZER, TurnKind.SYNTHESIS, ResearchIdea),
    (METHODOLOGIST, TurnKind.METHOD, MethodPlan),
    (CRITIC, TurnKind.CRITIQUE, Critique),
    (METHODOLOGIST, TurnKind.REVISION, RevisedProposal),
)


def _run_staff_turns(
    turns: list[TurnRecord],
    brief: str,
    thread_id: str,
    chat_model: ChatOpenAI,
) -> None:
    for role, kind, model in _STAFF_SEQUENCE:
        _append_turn(turns, role, kind, model, brief, thread_id, chat_model)


def run_round(round_index: int, brief: str, run_id: str) -> RoundRecord:
    """Execute all thirteen turns for one round.

    Parameters
    ----------
    round_index
        One-based round number (selects the seed role).
    brief
        Research brief text.
    run_id
        Study run identifier (required, non-empty).

    Returns
    -------
    RoundRecord
        Every turn in execution order.

    Raises
    ------
    ValueError
        When ``run_id`` is empty.
    """
    if not run_id:
        raise ValueError("run_id is required")
    openai_api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    langsmith_api_key = EnvVarsContainer.get_env_var("LANGSMITH_API_KEY", required=True)
    configure_tracing(langsmith_api_key)
    chat_model = build_chat_model(openai_api_key)
    thread_id = str(uuid7())
    seed_role = ROLE_ORDER[round_index - 1]
    turns: list[TurnRecord] = []
    _run_seed_turn(turns, seed_role, brief, thread_id, chat_model)
    _run_comment_passes(turns, seed_role, brief, thread_id, chat_model)
    _run_staff_turns(turns, brief, thread_id, chat_model)
    return RoundRecord(
        round_index=round_index,
        seed_role=seed_role.role_id,
        thread_id=thread_id,
        brief_sha256=brief_sha256(brief),
        turns=turns,
    )
