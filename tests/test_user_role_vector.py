"""Tests for the user-role vector mini-replication."""

from __future__ import annotations

import numpy as np
import pytest
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
    PROMPT_VARIANTS,
    average_role_activations,
    build_reflection_prompt,
    pair_role_activations,
    retain_valid_reflections,
)
from user_role_vector.style import score_user_likeness
from user_role_vector.synthetic import (
    run_mini_replication,
    simulate_reflection_activations,
)
from user_role_vector.traits import USER_ALIGNED_TRAITS


def test_difference_in_means_recovers_constant_offset() -> None:
    user = np.array([[2.0, 0.0], [4.0, 2.0]])
    assistant = np.array([[1.0, 0.0], [3.0, 2.0]])
    vector = extract_user_role_vector(user, assistant)
    np.testing.assert_allclose(vector, np.array([1.0, 0.0]))


def test_steer_activation_matches_equation_two() -> None:
    hidden = np.array([3.0, 4.0])
    role = np.array([1.0, 0.0])
    steered = steer_activation(hidden, role, alpha=0.2)
    np.testing.assert_allclose(steered, np.array([4.0, 4.0]))


def test_negative_alpha_reverses_the_shift() -> None:
    hidden = np.array([0.0, 2.0])
    role = np.array([0.0, 1.0])
    plus = steer_activation(hidden, role, 0.5)
    minus = steer_activation(hidden, role, -0.5)
    assert project_onto_direction(plus, role) > project_onto_direction(hidden, role)
    assert project_onto_direction(minus, role) < project_onto_direction(hidden, role)


def test_cosine_of_orthogonal_vectors_is_zero() -> None:
    assert cosine_similarity(
        np.array([1.0, 0.0]), np.array([0.0, 2.0])
    ) == pytest.approx(0.0)


def test_filter_drops_empty_and_long_dialogues() -> None:
    dialogues = [
        {
            "dialogue_id": "ok",
            "topic": "computer_programming",
            "turns": [
                {"role": "user", "content": "help"},
                {"role": "assistant", "content": "sure"},
            ],
        },
        {
            "dialogue_id": "empty",
            "topic": "other",
            "turns": [
                {"role": "user", "content": " "},
                {"role": "assistant", "content": "x"},
            ],
        },
        {
            "dialogue_id": "one",
            "topic": "other",
            "turns": [{"role": "user", "content": "hi"}],
        },
    ]
    kept = filter_dialogues(dialogues)
    assert [item["dialogue_id"] for item in kept] == ["ok"]


def test_stratified_sample_caps_each_topic() -> None:
    dialogues = []
    for index in range(5):
        dialogues.append(
            {
                "dialogue_id": f"a{index}",
                "topic": "computer_programming",
                "turns": [
                    {"role": "user", "content": "q"},
                    {"role": "assistant", "content": "a"},
                ],
            }
        )
        dialogues.append(
            {
                "dialogue_id": f"b{index}",
                "topic": "write_fiction",
                "turns": [
                    {"role": "user", "content": "q"},
                    {"role": "assistant", "content": "a"},
                ],
            }
        )
    sample = stratified_sample(dialogues, per_category=2, seed=1)
    topics = [item["topic"] for item in sample]
    assert topics.count("computer_programming") == 2
    assert topics.count("write_fiction") == 2


def test_reflection_prompt_includes_role_and_dialogue() -> None:
    prompt = build_reflection_prompt(
        role="user",
        dialogue_text="User: hi Assistant: hello",
        variant="role_simulation",
    )
    assert "simulating the role of the user" in prompt
    assert "User: hi Assistant: hello" in prompt
    assert "exactly one paragraph" in prompt


def test_retain_valid_reflections_drops_not_represented() -> None:
    records = [
        {"dialogue_id": "d1", "validation": "strongly_represented"},
        {"dialogue_id": "d2", "validation": "not_represented"},
        {"dialogue_id": "d3", "validation": "weakly_represented"},
    ]
    kept = retain_valid_reflections(records)
    assert [item["dialogue_id"] for item in kept] == ["d1", "d3"]


def test_pair_and_average_activations() -> None:
    records = [
        {
            "dialogue_id": "d1",
            "variant": "role_simulation",
            "role": "user",
            "activation": [2.0, 0.0],
        },
        {
            "dialogue_id": "d1",
            "variant": "role_simulation",
            "role": "assistant",
            "activation": [0.0, 0.0],
        },
        {
            "dialogue_id": "d1",
            "variant": "transcript_analysis",
            "role": "user",
            "activation": [4.0, 0.0],
        },
        {
            "dialogue_id": "d1",
            "variant": "transcript_analysis",
            "role": "assistant",
            "activation": [2.0, 0.0],
        },
    ]
    user, assistant = pair_role_activations(records)
    assert user.shape == (2, 2)
    mean_user, mean_assistant = average_role_activations(records)
    np.testing.assert_allclose(mean_user[0], np.array([3.0, 0.0]))
    np.testing.assert_allclose(mean_assistant[0], np.array([1.0, 0.0]))


def test_user_like_message_scores_higher_than_assistant_like() -> None:
    user = score_user_likeness("best headphones for flights?")
    assistant = score_user_likeness(
        "Could you please assist me in drafting a detailed comparison of three "
        "headphones, including comfort, battery life, price, and travel use?"
    )
    assert user["mean"] > assistant["mean"]
    assert user["brevity"] > assistant["brevity"]
    assert user["informality"] > assistant["informality"]


def test_first_disengage_turn_and_rates() -> None:
    predicted = first_disengage_turn(
        ["continue", "continue", "disengage", "continue"],
        final_turn=4,
    )
    assert predicted == 3
    assert disengagement_distance(3, 8) == 5
    assert exact_match_rate([8, 3], [8, 3]) == 1.0
    assert disengagement_rate([3, 8, 2], final_turn=8) == pytest.approx(2 / 3)


def test_mini_replication_recovers_planted_direction() -> None:
    results = run_mini_replication(seed=0)
    assert results["recovery_cosine"] > 0.9
    assert results["paired_recovery_cosine"] > 0.9
    assert results["steered_projection"]["0.3"] > results["steered_projection"]["0.0"]
    assert results["steered_projection"]["-0.3"] < results["steered_projection"]["0.0"]
    user_aligned = [
        row["cosine"]
        for row in results["trait_cosines"]
        if row["trait"] in USER_ALIGNED_TRAITS
    ]
    assistant_aligned = [
        row["cosine"]
        for row in results["trait_cosines"]
        if row["trait"] not in USER_ALIGNED_TRAITS
    ]
    assert min(user_aligned) > max(assistant_aligned)


def test_zero_vector_cannot_be_steered() -> None:
    with pytest.raises(ValueError, match="zero vector"):
        steer_activation(np.array([1.0, 0.0]), np.array([0.0, 0.0]), 0.1)


def test_mismatched_activation_shapes_fail() -> None:
    with pytest.raises(ValueError, match="shape"):
        extract_user_role_vector(np.ones((2, 3)), np.ones((2, 4)))


def test_simulate_reflection_activations_has_both_roles() -> None:
    records, planted = simulate_reflection_activations(n_dialogues=2, hidden_size=8)
    assert planted.shape == (8,)
    roles = {record["role"] for record in records}
    assert roles == {"user", "assistant"}
    assert len(records) == 2 * 3 * 2


def test_qwen_job_dialogues_pass_the_paper_filter() -> None:
    from user_role_vector.qwen_experiment import (
        HANDCRAFTED_DIALOGUES,
        USER_GOALS,
        mean_style_by_alpha,
        validated_dialogues,
    )

    kept = validated_dialogues()
    assert len(kept) == 8
    assert {item["dialogue_id"] for item in kept} == {
        item["dialogue_id"] for item in HANDCRAFTED_DIALOGUES
    }
    assert len(USER_GOALS) == 5
    prompt = build_reflection_prompt(
        role="user",
        dialogue_text="User: hi Assistant: hello",
        variant=PROMPT_VARIANTS[0],
    )
    assert "exactly one paragraph" in prompt
    summary = mean_style_by_alpha(
        [
            {
                "alpha": 0.0,
                "brevity": 2.0,
                "informality": 2.0,
                "information_pacing": 2.0,
                "mean": 2.0,
                "word_count": 10,
            },
            {
                "alpha": 0.3,
                "brevity": 4.0,
                "informality": 4.0,
                "information_pacing": 4.0,
                "mean": 4.0,
                "word_count": 4,
            },
        ]
    )
    assert summary[0]["mean"] == 2.0
    assert summary[1]["alpha"] == 0.3


def test_qwen_job_script_declares_uv_dependencies() -> None:
    from pathlib import Path

    script = Path(
        "autoresearch/assistant_bias_user_role_vector_2026_09_09/"
        "scripts/qwen_role_vector_job.py"
    )
    text = script.read_text(encoding="utf-8")
    assert text.startswith("# /// script")
    assert "transformers>=5.17.0" in text
    assert "Qwen/Qwen3.5-4B" in text
    assert "enable_thinking" in text
