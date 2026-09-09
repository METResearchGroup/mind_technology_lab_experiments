"""LMSYS-style dialogue filtering and topic-balanced sampling."""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import TypedDict

TOPIC_CATEGORIES: tuple[str, ...] = (
    "specific_info",
    "computer_programming",
    "edit_or_critique_provided_text",
    "greetings_and_chitchat",
    "write_fiction",
    "tutoring_or_teaching",
    "how_to_advice",
    "other",
    "personal_writing_or_communication",
    "asking_about_the_model",
    "mathematical_calculation",
    "games_and_role_play",
    "argument_or_summary_generation",
    "creative_ideation",
    "translation",
    "unclear",
    "health_fitness_beauty_or_self_care",
    "relationships_and_personal_reflection",
    "purchasable_products",
    "create_an_image",
    "data_analysis",
    "cooking_and_recipes",
    "analyze_an_image",
    "generate_or_retrieve_other_media",
)

VALID_ROLES = frozenset({"user", "assistant"})


class Turn(TypedDict):
    role: str
    content: str


class Dialogue(TypedDict):
    dialogue_id: str
    turns: list[Turn]
    topic: str


def _turn_count(dialogue: Mapping[str, object]) -> int:
    turns = dialogue.get("turns", [])
    if not isinstance(turns, Sequence) or isinstance(turns, (str, bytes)):
        return 0
    return len(turns)


def _turns_are_valid(dialogue: Mapping[str, object]) -> bool:
    turns = dialogue.get("turns", [])
    if not isinstance(turns, Sequence) or isinstance(turns, (str, bytes)):
        return False
    for turn in turns:
        if not isinstance(turn, Mapping):
            return False
        role = turn.get("role")
        content = turn.get("content")
        if role not in VALID_ROLES:
            return False
        if not isinstance(content, str) or content.strip() == "":
            return False
    return True


def filter_dialogues(
    dialogues: Sequence[Mapping[str, object]],
    *,
    min_turns: int = 2,
    max_turns: int = 50,
) -> list[Dialogue]:
    """Keep dialogues with 2-50 valid, non-empty user/assistant turns."""
    kept: list[Dialogue] = []
    for dialogue in dialogues:
        n_turns = _turn_count(dialogue)
        if n_turns < min_turns or n_turns > max_turns:
            continue
        if not _turns_are_valid(dialogue):
            continue
        kept.append(
            {
                "dialogue_id": str(dialogue.get("dialogue_id", "")),
                "turns": list(dialogue["turns"]),  # type: ignore[arg-type]
                "topic": str(dialogue.get("topic", "unclear")),
            }
        )
    return kept


def stratified_sample(
    dialogues: Sequence[Dialogue],
    *,
    per_category: int = 30,
    seed: int = 0,
) -> list[Dialogue]:
    """Draw up to ``per_category`` dialogues from each topic label."""
    rng = random.Random(seed)
    by_topic: dict[str, list[Dialogue]] = defaultdict(list)
    for dialogue in dialogues:
        topic = str(dialogue.get("topic", "unclear"))
        by_topic[topic].append(dialogue)
    sampled: list[Dialogue] = []
    for topic in TOPIC_CATEGORIES:
        pool = list(by_topic.get(topic, []))
        rng.shuffle(pool)
        sampled.extend(pool[:per_category])
    return sampled
