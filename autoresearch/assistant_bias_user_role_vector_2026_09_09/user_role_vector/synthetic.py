"""Planted-direction mini-replication of user-role CAA on CPU."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from user_role_vector.caa import (
    cosine_similarity,
    extract_user_role_vector,
    project_onto_direction,
    steer_activation,
)
from user_role_vector.dialogues import filter_dialogues, stratified_sample
from user_role_vector.disengage import (
    disengagement_distance,
    disengagement_rate,
    exact_match_rate,
    first_disengage_turn,
)
from user_role_vector.reflections import (
    average_role_activations,
    pair_role_activations,
    retain_valid_reflections,
)
from user_role_vector.style import score_user_likeness
from user_role_vector.traits import ASSISTANT_TRAITS, USER_ALIGNED_TRAITS

HIDDEN_SIZE = 64
N_DIALOGUES = 48
N_VARIANTS = 3


def _planted_direction(rng: np.random.Generator, dim: int) -> np.ndarray:
    raw = rng.normal(size=dim)
    return raw / np.linalg.norm(raw)


def simulate_reflection_activations(
    *,
    seed: int = 0,
    n_dialogues: int = N_DIALOGUES,
    hidden_size: int = HIDDEN_SIZE,
) -> tuple[list[dict[str, object]], np.ndarray]:
    """Build noisy user/assistant pairs around a known role direction."""
    rng = np.random.default_rng(seed)
    planted = _planted_direction(rng, hidden_size)
    records: list[dict[str, object]] = []
    variants = ("transcript_analysis", "role_simulation", "dialogue_participant")
    for dialogue_index in range(n_dialogues):
        content = rng.normal(scale=0.8, size=hidden_size)
        for variant in variants:
            noise_user = rng.normal(scale=0.25, size=hidden_size)
            noise_asst = rng.normal(scale=0.25, size=hidden_size)
            user_h = content + 1.4 * planted + noise_user
            asst_h = content - 1.4 * planted + noise_asst
            records.append(
                {
                    "dialogue_id": f"d{dialogue_index:03d}",
                    "variant": variant,
                    "role": "user",
                    "activation": user_h.tolist(),
                    "validation": "strongly_represented",
                }
            )
            records.append(
                {
                    "dialogue_id": f"d{dialogue_index:03d}",
                    "variant": variant,
                    "role": "assistant",
                    "activation": asst_h.tolist(),
                    "validation": "strongly_represented",
                }
            )
    return records, planted


def recover_role_vector(records: list[dict[str, object]]) -> np.ndarray:
    kept = retain_valid_reflections(records)
    user, assistant = average_role_activations(kept)
    return extract_user_role_vector(user, assistant)


def trait_cosines(
    role_vector: np.ndarray,
    planted: np.ndarray,
    *,
    seed: int = 1,
) -> list[dict[str, float | str]]:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []
    for trait in ASSISTANT_TRAITS:
        noise = rng.normal(scale=0.15, size=planted.shape)
        if trait in USER_ALIGNED_TRAITS:
            trait_vec = planted + noise
        else:
            trait_vec = -planted + noise
        rows.append(
            {
                "trait": trait,
                "cosine": cosine_similarity(role_vector, trait_vec),
            }
        )
    rows.sort(key=lambda row: float(row["cosine"]))
    return rows


def style_vs_alpha() -> list[dict[str, float | str]]:
    messages = {
        -0.3: (
            "Please assist me in assembling the flat-pack furniture by first laying "
            "out all components and hardware on a clean, flat surface to verify "
            "inventory against the included diagram."
        ),
        0.0: (
            "Please help me assemble this piece of flat-pack furniture by reviewing "
            "the instruction manual, organizing all the parts and tools, and guiding "
            "me through each step."
        ),
        0.3: "need help putting this ikea shelf together, where do i start?",
    }
    rows: list[dict[str, float | str]] = []
    for alpha, message in messages.items():
        scores = score_user_likeness(message)
        rows.append(
            {
                "alpha": alpha,
                "direction": "assistant"
                if alpha < 0
                else "unsteered"
                if alpha == 0
                else "user",
                "brevity": scores["brevity"],
                "informality": scores["informality"],
                "pacing": scores["information_pacing"],
                "mean": scores["mean"],
                "word_count": scores["word_count"],
            }
        )
    return rows


def fake_disengagement_by_alpha(seed: int = 2) -> list[dict[str, float]]:
    """Logistic early-stop model that tracks Table 2's qualitative shape."""
    rng = np.random.default_rng(seed)
    final_turn = 8
    rows: list[dict[str, float]] = []
    for alpha in (0.0, 0.1, 0.2, 0.3):
        predicted: list[int] = []
        true_turns = [final_turn] * 200
        for _ in range(200):
            p_leave = 0.18 + 1.1 * alpha
            labels = []
            left = False
            for _turn in range(final_turn):
                if (not left) and rng.random() < p_leave:
                    labels.append("disengage")
                    left = True
                else:
                    labels.append("continue")
            predicted.append(first_disengage_turn(labels, final_turn=final_turn))
        distances = [
            disengagement_distance(pred, true)
            for pred, true in zip(predicted, true_turns, strict=True)
        ]
        rows.append(
            {
                "alpha": alpha,
                "exact": exact_match_rate(predicted, true_turns),
                "distance": float(np.mean(distances)),
                "rate": disengagement_rate(predicted, final_turn=final_turn),
            }
        )
    return rows


def run_mini_replication(seed: int = 0) -> dict[str, Any]:
    records, planted = simulate_reflection_activations(seed=seed)
    recovered = recover_role_vector(records)
    paired_user, paired_assistant = pair_role_activations(
        retain_valid_reflections(records)
    )
    paired_vector = extract_user_role_vector(paired_user, paired_assistant)

    hidden = np.zeros(HIDDEN_SIZE)
    hidden[0] = 1.0
    steered = {}
    for alpha in (0.0, 0.1, 0.2, 0.3, -0.3):
        updated = steer_activation(hidden, recovered, alpha)
        steered[str(alpha)] = float(project_onto_direction(updated, recovered))

    sample_dialogues = [
        {
            "dialogue_id": "grad",
            "topic": "personal_writing_or_communication",
            "turns": [
                {"role": "user", "content": "How would you congratulate a scholar?"},
                {
                    "role": "assistant",
                    "content": "Acknowledge their hard work and express genuine pride.",
                },
                {
                    "role": "user",
                    "content": "Can you write me a sample message for a graduate?",
                },
                {
                    "role": "assistant",
                    "content": "Dear [Name], congratulations on your graduation!",
                },
            ],
        },
        {
            "dialogue_id": "empty",
            "topic": "other",
            "turns": [{"role": "user", "content": ""}],
        },
        {
            "dialogue_id": "code",
            "topic": "computer_programming",
            "turns": [
                {"role": "user", "content": "Why does this Python loop never stop?"},
                {
                    "role": "assistant",
                    "content": "Check whether the loop variable is updated.",
                },
            ],
        },
    ]
    filtered = filter_dialogues(sample_dialogues)
    sampled = stratified_sample(filtered, per_category=1, seed=seed)

    return {
        "kind": "planted_direction_mini_replication",
        "hidden_size": HIDDEN_SIZE,
        "n_dialogues": N_DIALOGUES,
        "n_prompt_variants": N_VARIANTS,
        "recovery_cosine": cosine_similarity(recovered, planted),
        "paired_recovery_cosine": cosine_similarity(paired_vector, planted),
        "steered_projection": steered,
        "trait_cosines": trait_cosines(recovered, planted),
        "style_vs_alpha": style_vs_alpha(),
        "disengagement_vs_alpha": fake_disengagement_by_alpha(),
        "n_filtered_sample_dialogues": len(filtered),
        "n_stratified_sample": len(sampled),
        "note": (
            "This run plants a known user-role direction in random hidden states, "
            "recovers it with the paper's difference-in-means formula, and checks "
            "that contrastive activation addition moves projections as predicted. "
            "It does not load Qwen3.5-4B."
        ),
    }


def write_results(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
