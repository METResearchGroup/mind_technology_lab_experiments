from turing_rl.dataset import get_examples
from turing_rl.grpo import group_advantages, softmax, update_logits
from turing_rl.judge import similarity_score, turing_likert
from turing_rl.rewards import (
    LengthPenaltyConfig,
    clip_turing_judge_score,
    combine_turing_reward,
    length_penalty,
    turing_reward,
    word_count,
)
from turing_rl.train import run_mini_replication


def test_turing_reward_matches_paper_mapping() -> None:
    assert turing_reward(1.0) == 0.0
    assert turing_reward(4.0) == 0.5
    assert turing_reward(5.0) == 4.0 / 6.0
    assert turing_reward(7.0) == turing_reward(5.0)
    assert clip_turing_judge_score(7.0) == 5.0


def test_official_scale_multiplies_paper_mapping() -> None:
    assert turing_reward(5.0, apply_official_scale=True) == (4.0 / 6.0) * 0.9


def test_length_penalty_is_zero_inside_deadband() -> None:
    config = LengthPenaltyConfig.for_domain("reddit")
    ground = "one two three four five six seven eight nine ten"
    response = "one two three four five six seven eight"
    assert 0.8 <= word_count(response) / word_count(ground) <= 1.1
    assert length_penalty(response, ground, config) == 0.0


def test_length_penalty_caps_and_penalizes_short_replies() -> None:
    config = LengthPenaltyConfig.for_domain("reddit")
    ground = "one two three four five six seven eight nine ten"
    penalty = length_penalty("one", ground, config)
    ratio = 1 / 10
    expected = min(0.45 * ((0.8 - ratio) / 0.8), 0.25)
    assert abs(penalty - expected) < 1e-9


def test_combine_turing_reward_never_goes_negative() -> None:
    config = LengthPenaltyConfig(
        r_min=0.8,
        r_max=1.1,
        lambda_short=5.0,
        lambda_long=5.0,
        penalty_cap=5.0,
    )
    value = combine_turing_reward(1.0, "short", "one two three four five six", config)
    assert value == 0.0


def test_group_advantages_are_zero_when_rewards_match() -> None:
    assert group_advantages([0.4, 0.4, 0.4, 0.4]) == [0.0, 0.0, 0.0, 0.0]


def test_group_advantages_standardize_a_group() -> None:
    advantages = group_advantages([0.0, 1.0, 2.0, 3.0])
    mean = sum(advantages) / 4
    second_moment = sum(value * value for value in advantages) / 4
    assert advantages[3] > advantages[0]
    assert abs(mean) < 1e-9
    assert abs(second_moment - 1.0) < 1e-9


def test_softmax_update_raises_the_winning_action() -> None:
    logits = [0.0, 0.0, 0.0]
    updated = update_logits(
        logits, [2, 2, 2, 2], [1.0, 1.0, 1.0, 1.0], learning_rate=0.5
    )
    probabilities = softmax(updated)
    assert probabilities[2] > probabilities[0]
    assert probabilities[2] > probabilities[1]


def test_turing_judge_prefers_human_like_over_assistant() -> None:
    example = get_examples()[0]
    by_id = {candidate.id: candidate.text for candidate in example.candidates}
    human = turing_likert(
        by_id["human_like"], example.ground_truth, example.history_profile
    )
    assistant = turing_likert(
        by_id["assistant_like"],
        example.ground_truth,
        example.history_profile,
    )
    assert human > assistant


def test_similarity_judge_prefers_content_overlap() -> None:
    example = get_examples()[0]
    by_id = {candidate.id: candidate.text for candidate in example.candidates}
    content = similarity_score(by_id["content_match"], example.ground_truth)
    assistant = similarity_score(by_id["assistant_like"], example.ground_truth)
    assert content > assistant


def test_mini_replication_turing_mass_moves_to_human_like() -> None:
    payload = run_mini_replication(seed=7)
    turing_rows = [
        row for row in payload["replica"]["summary"] if row["method"] == "turing"
    ]
    assert turing_rows
    assert all(row["human_like_prob"] > 0.45 for row in turing_rows)
    assert all(row["mode_kind"] == "human_like" for row in turing_rows)
