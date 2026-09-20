"""Role-specific reflection prompts and pairing from Appendix E.1."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Literal

import numpy as np
from numpy.typing import NDArray

Role = Literal["user", "assistant"]
PromptVariant = Literal[
    "transcript_analysis",
    "role_simulation",
    "dialogue_participant",
]
ValidationLabel = Literal[
    "strongly_represented",
    "weakly_represented",
    "not_represented",
]

PROMPT_VARIANTS: tuple[PromptVariant, ...] = (
    "transcript_analysis",
    "role_simulation",
    "dialogue_participant",
)

_INTROS: dict[PromptVariant, str] = {
    "transcript_analysis": (
        "You are analyzing the following dialogue from the perspective of the {role}."
    ),
    "role_simulation": (
        "You are simulating the role of the {role} in the following dialogue."
    ),
    "dialogue_participant": "You are the {role} in the following dialogue.",
}

_REFLECTION_QUESTION = (
    "Instruction: Write a brief reflection from the {role}'s perspective "
    "in one paragraph. Write exactly one paragraph."
)

VALID_LABELS = frozenset(
    {"strongly_represented", "weakly_represented", "not_represented"}
)


def format_dialogue_text(turns: Sequence[Mapping[str, str]]) -> str:
    lines: list[str] = []
    for turn in turns:
        role = str(turn["role"]).capitalize()
        lines.append(f"{role}: {turn['content']}")
    return " ".join(lines)


def build_reflection_prompt(
    *,
    role: Role,
    dialogue_text: str,
    variant: PromptVariant,
) -> str:
    intro = _INTROS[variant].format(role=role)
    question = _REFLECTION_QUESTION.format(role=role)
    return f"{intro} Dialogue: {dialogue_text} {question}"


def retain_valid_reflections(
    records: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Drop reflections labeled ``not_represented`` (Appendix A.2.2)."""
    kept: list[dict[str, object]] = []
    for record in records:
        label = record.get("validation")
        if label not in VALID_LABELS:
            raise ValueError(f"unknown validation label: {label!r}")
        if label == "not_represented":
            continue
        kept.append(dict(record))
    return kept


def pair_role_activations(
    records: Sequence[Mapping[str, object]],
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Pair user and assistant activations by dialogue and prompt variant."""
    keyed: dict[tuple[object, object, object], Mapping[str, object]] = {}
    for record in records:
        key = (record.get("dialogue_id"), record.get("variant"), record.get("role"))
        keyed[key] = record
    user_rows: list[NDArray[np.floating]] = []
    assistant_rows: list[NDArray[np.floating]] = []
    pairs = {
        (dialogue_id, variant)
        for dialogue_id, variant, role in keyed
        if role in {"user", "assistant"}
    }
    for dialogue_id, variant in sorted(
        pairs, key=lambda item: (str(item[0]), str(item[1]))
    ):
        user = keyed.get((dialogue_id, variant, "user"))
        assistant = keyed.get((dialogue_id, variant, "assistant"))
        if user is None or assistant is None:
            continue
        user_rows.append(np.asarray(user["activation"], dtype=np.float64))
        assistant_rows.append(np.asarray(assistant["activation"], dtype=np.float64))
    if not user_rows:
        raise ValueError("no paired user/assistant activations")
    return np.stack(user_rows), np.stack(assistant_rows)


def average_role_activations(
    records: Sequence[Mapping[str, object]],
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Mean activations per dialogue across prompt variants, then stack pairs."""
    grouped: dict[tuple[object, object], list[NDArray[np.floating]]] = defaultdict(list)
    for record in records:
        key = (record.get("dialogue_id"), record.get("role"))
        grouped[key].append(np.asarray(record["activation"], dtype=np.float64))
    dialogue_ids = sorted(
        {dialogue_id for dialogue_id, role in grouped if role in {"user", "assistant"}},
        key=str,
    )
    user_rows: list[NDArray[np.floating]] = []
    assistant_rows: list[NDArray[np.floating]] = []
    for dialogue_id in dialogue_ids:
        user_list = grouped.get((dialogue_id, "user"))
        assistant_list = grouped.get((dialogue_id, "assistant"))
        if not user_list or not assistant_list:
            continue
        user_rows.append(np.mean(np.stack(user_list), axis=0))
        assistant_rows.append(np.mean(np.stack(assistant_list), axis=0))
    if not user_rows:
        raise ValueError("no dialogues with both roles")
    return np.stack(user_rows), np.stack(assistant_rows)
