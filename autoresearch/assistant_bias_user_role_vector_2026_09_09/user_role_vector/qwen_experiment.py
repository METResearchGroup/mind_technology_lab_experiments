"""Hand-crafted Qwen 3.5 4B job inputs shared by tests and the dashboard.

The Hugging Face Job script is self-contained (Jobs only upload that one
file). Keep the dialogues and goals here in sync with
``scripts/qwen_role_vector_job.py``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from user_role_vector.dialogues import Dialogue, filter_dialogues

QWEN_MODEL_ID = "Qwen/Qwen3.5-4B"
STEER_LAYER_INDEX = 11
ALPHAS: tuple[float, ...] = (-0.3, 0.0, 0.1, 0.2, 0.3)
S3_BUCKET = "mind-technology-lab-experiments"
S3_PREFIX = "autoresearch/assistant_bias_user_role_vector_2026_09_09/"
S3_REGION = "us-east-2"

USER_SIMULATOR_INSTRUCTION = (
    "You are simulating a human user talking to an AI assistant. "
    "Write only the user's first message. Do not write the assistant's reply. "
    "Do not mention that you are a simulator. Goal: {goal}"
)

HANDCRAFTED_DIALOGUES: list[Dialogue] = [
    {
        "dialogue_id": "furniture",
        "topic": "how_to_advice",
        "turns": [
            {
                "role": "user",
                "content": "I bought a flat-pack desk and the instructions are terrible.",
            },
            {
                "role": "assistant",
                "content": (
                    "I can walk you through it. Start by laying out every panel "
                    "and bag of screws and matching them to the parts list."
                ),
            },
            {
                "role": "user",
                "content": "Okay, I have two identical side panels and a bag labeled C.",
            },
            {
                "role": "assistant",
                "content": (
                    "Bag C is usually the cam locks. Attach the side panels to "
                    "the desktop first, cams facing inward, before you add the legs."
                ),
            },
        ],
    },
    {
        "dialogue_id": "headphones",
        "topic": "purchasable_products",
        "turns": [
            {
                "role": "user",
                "content": "Need noise-canceling headphones for a long-haul flight.",
            },
            {
                "role": "assistant",
                "content": (
                    "Look at comfort, battery life, and how strong the ANC is at "
                    "engine rumble frequencies. A few popular options sit around $200-350."
                ),
            },
            {
                "role": "user",
                "content": "I don't want to spend more than $250 and I wear glasses.",
            },
            {
                "role": "assistant",
                "content": (
                    "Then prioritize padding that doesn't clamp the temples. "
                    "Several mid-range models last over 20 hours and fold into a case."
                ),
            },
        ],
    },
    {
        "dialogue_id": "invite",
        "topic": "personal_writing_or_communication",
        "turns": [
            {
                "role": "user",
                "content": "I need to decline a dinner invite without sounding rude.",
            },
            {
                "role": "assistant",
                "content": (
                    "Keep it short: thank them, say you cannot make it, and offer "
                    "another time if you mean it."
                ),
            },
            {
                "role": "user",
                "content": "It's a coworker I like. I just already have plans.",
            },
            {
                "role": "assistant",
                "content": (
                    "Say you appreciate the invite and already have a commitment "
                    "that night. Suggest coffee later in the week."
                ),
            },
        ],
    },
    {
        "dialogue_id": "return",
        "topic": "purchasable_products",
        "turns": [
            {
                "role": "user",
                "content": "The zipper on the jacket I ordered last week already broke.",
            },
            {
                "role": "assistant",
                "content": (
                    "Most shops will take a defective zipper as a return or "
                    "replacement. Do you still have the order number?"
                ),
            },
            {"role": "user", "content": "Yes, 48291. I just want a refund."},
            {
                "role": "assistant",
                "content": (
                    "Write that the zipper failed after a few uses, attach a photo, "
                    "and ask for a refund to the original payment method."
                ),
            },
        ],
    },
    {
        "dialogue_id": "algebra",
        "topic": "tutoring_or_teaching",
        "turns": [
            {
                "role": "user",
                "content": "I moved the x terms to the left and I think I dropped a sign.",
            },
            {
                "role": "assistant",
                "content": (
                    "Show me the line before and after the move. A missing minus "
                    "is the usual failure when both sides have x."
                ),
            },
            {
                "role": "user",
                "content": "I had 3x - 5 = 1 - 2x and I wrote 3x + 2x = 1 + 5.",
            },
            {
                "role": "assistant",
                "content": (
                    "That is correct: adding 2x and adding 5 to both sides. "
                    "Next divide 5x = 6."
                ),
            },
        ],
    },
    {
        "dialogue_id": "debug",
        "topic": "computer_programming",
        "turns": [
            {
                "role": "user",
                "content": "My Python script crashes with a KeyError on 'user_id'.",
            },
            {
                "role": "assistant",
                "content": (
                    "Print the dict keys just before the lookup. Either the API "
                    "renamed the field or you are parsing a nested object."
                ),
            },
            {
                "role": "user",
                "content": "It is nested under data.profile. The top level has status.",
            },
            {
                "role": "assistant",
                "content": (
                    "Then read payload['data']['profile']['user_id'] after you "
                    "check that status is ok."
                ),
            },
        ],
    },
    {
        "dialogue_id": "recipe",
        "topic": "cooking_and_recipes",
        "turns": [
            {
                "role": "user",
                "content": "I want a weeknight pasta that uses only pantry stuff.",
            },
            {
                "role": "assistant",
                "content": (
                    "Garlic, olive oil, chili flakes, and pasta water make a "
                    "sauce in the time it takes the noodles to cook."
                ),
            },
            {
                "role": "user",
                "content": "I have a can of tomatoes and some parmesan too.",
            },
            {
                "role": "assistant",
                "content": (
                    "Simmer the tomatoes with garlic for ten minutes, toss with "
                    "pasta, and finish with cheese and pasta water."
                ),
            },
        ],
    },
    {
        "dialogue_id": "chitchat",
        "topic": "greetings_and_chitchat",
        "turns": [
            {"role": "user", "content": "Hey, just killing time before a meeting."},
            {
                "role": "assistant",
                "content": "Happy to chat. What is the meeting about, or do you want a distraction?",
            },
            {
                "role": "user",
                "content": "It's a status update. I already sent the slides.",
            },
            {
                "role": "assistant",
                "content": (
                    "Then you are in good shape. If you want, we can brainstorm "
                    "one sentence that summarizes the week."
                ),
            },
        ],
    },
]

USER_GOALS: tuple[dict[str, str], ...] = (
    {
        "id": "furniture",
        "goal": "Assemble a piece of flat-pack furniture",
    },
    {
        "id": "headphones",
        "goal": "Choose noise-canceling headphones for flights",
    },
    {
        "id": "invite",
        "goal": "Decline a dinner invitation politely",
    },
    {
        "id": "return",
        "goal": "Return a jacket with a broken zipper",
    },
    {
        "id": "algebra",
        "goal": "Ask a tutor about a confusing algebra step",
    },
)


def validated_dialogues(
    dialogues: Sequence[Mapping[str, object]] | None = None,
) -> list[Dialogue]:
    source = HANDCRAFTED_DIALOGUES if dialogues is None else dialogues
    kept = filter_dialogues(source)
    if len(kept) != len(source):
        raise ValueError("handcrafted dialogues failed the 2-50 turn filter")
    return kept


def mean_style_by_alpha(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, float | str]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        key = str(row["alpha"])
        grouped.setdefault(key, []).append(row)
    summary: list[dict[str, float | str]] = []
    for alpha in sorted(grouped, key=float):
        items = grouped[alpha]
        n = max(len(items), 1)
        summary.append(
            {
                "alpha": float(alpha),
                "brevity": sum(float(item["brevity"]) for item in items) / n,
                "informality": sum(float(item["informality"]) for item in items) / n,
                "information_pacing": sum(
                    float(item["information_pacing"]) for item in items
                )
                / n,
                "mean": sum(float(item["mean"]) for item in items) / n,
                "word_count": sum(float(item["word_count"]) for item in items) / n,
            }
        )
    return summary
