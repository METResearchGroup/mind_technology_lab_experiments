"""Survey and deliberation metrics from arXiv:2609.07573."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from personas import Persona
from questions import DIVISIVE_CUTOFF, Question


@dataclass(frozen=True)
class GroupShare:
    question_id: str
    axis: str
    group: str
    persona_share: float | None
    human_share: float
    n: int


def a_share(choices: Sequence[str | None]) -> float | None:
    valid = [choice for choice in choices if choice in {"A", "B"}]
    if not valid:
        return None
    return 100.0 * sum(choice == "A" for choice in valid) / len(valid)


def mean_absolute_gap(rows: Sequence[GroupShare]) -> float | None:
    gaps = [
        abs(row.persona_share - row.human_share)
        for row in rows
        if row.persona_share is not None
    ]
    if not gaps:
        return None
    return sum(gaps) / len(gaps)


def group_rows(
    question: Question,
    personas: Sequence[Persona],
    choices: dict[str, str | None],
) -> list[GroupShare]:
    rows: list[GroupShare] = []
    for axis in question.axes:
        human_groups = question.human_by_group.get(axis, {})
        buckets: dict[str, list[str | None]] = defaultdict(list)
        for persona in personas:
            key = getattr(persona, axis)
            if key is None:
                continue
            buckets[str(key)].append(choices.get(persona.id))
        for group, human_share in human_groups.items():
            share = a_share(buckets.get(group, []))
            rows.append(
                GroupShare(
                    question_id=question.id,
                    axis=axis,
                    group=group,
                    persona_share=share,
                    human_share=human_share,
                    n=len(buckets.get(group, [])),
                )
            )
    return rows


def direction_matches(rows: Sequence[GroupShare]) -> tuple[int, int]:
    """Count pairwise within-axis orderings that match the human survey."""
    by_key: dict[tuple[str, str], list[GroupShare]] = defaultdict(list)
    for row in rows:
        by_key[(row.question_id, row.axis)].append(row)
    matches = 0
    total = 0
    for group_rows_for_axis in by_key.values():
        n = len(group_rows_for_axis)
        for i in range(n):
            for j in range(i + 1, n):
                left = group_rows_for_axis[i]
                right = group_rows_for_axis[j]
                if left.persona_share is None or right.persona_share is None:
                    continue
                human_delta = left.human_share - right.human_share
                persona_delta = left.persona_share - right.persona_share
                if human_delta == 0:
                    continue
                total += 1
                if (persona_delta > 0) == (human_delta > 0):
                    matches += 1
    return matches, total


def is_divisive(share: float | None) -> bool:
    if share is None:
        return False
    return share < DIVISIVE_CUTOFF and (100.0 - share) < DIVISIVE_CUTOFF


def concentration_flags(rows: Sequence[GroupShare], near: float = 2.0) -> int:
    count = 0
    for row in rows:
        if row.persona_share is None:
            continue
        if row.persona_share <= near or row.persona_share >= 100.0 - near:
            count += 1
    return count


def movement_rate(
    start: Sequence[str | None], end: Sequence[str | None]
) -> float | None:
    pairs = [
        (left, right)
        for left, right in zip(start, end, strict=True)
        if left in {"A", "B"} and right in {"A", "B"}
    ]
    if not pairs:
        return None
    return sum(left != right for left, right in pairs) / len(pairs)


def mean(values: Iterable[float]) -> float | None:
    data = list(values)
    if not data:
        return None
    return sum(data) / len(data)
