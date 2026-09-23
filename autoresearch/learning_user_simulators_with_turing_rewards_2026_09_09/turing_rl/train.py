"""Run a dummy-data GRPO comparison of Turing, Sim, and Logprob rewards."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from turing_rl.dataset import Example, get_examples
from turing_rl.grpo import group_advantages, sample_actions, softmax, update_logits
from turing_rl.judge import similarity_score, turing_likert
from turing_rl.rewards import (
    LengthPenaltyConfig,
    combine_turing_reward,
    mean_gt_logprob,
)

GROUP_SIZE = 4
STEPS = 80
LEARNING_RATE = 0.35
KL_COEFFICIENT = 0.001
SEED = 7

PAPER_HUMAN_WIN_RATES = {
    "chat": {
        "SFT-Init": {"mean": 0.49, "ci": 0.061},
        "Sim-RL": {"mean": 0.50, "ci": 0.055},
        "Turing-RL": {"mean": 0.57, "ci": 0.050},
    },
    "reddit": {
        "SFT-Init": {"mean": 0.41, "ci": 0.045},
        "Sim-RL": {"mean": 0.52, "ci": 0.049},
        "Turing-RL": {"mean": 0.50, "ci": 0.051},
    },
}

PAPER_TURING_RL_ABLATION = {
    "chat": {
        "history_persona": {"turing": 4.31, "sim": 5.3, "specificity": 0.512},
        "history": {"turing": 4.26, "sim": 4.7, "specificity": 0.497},
        "persona": {"turing": 4.23, "sim": 4.1, "specificity": 0.509},
    },
    "reddit": {
        "history_persona": {"turing": 3.68, "sim": 3.0, "specificity": 0.367},
        "history": {"turing": 3.78, "sim": 3.3, "specificity": 0.364},
        "persona": {"turing": 3.84, "sim": 2.7, "specificity": 0.329},
    },
}


def candidate_rewards(example: Example, method: str) -> list[float]:
    config = LengthPenaltyConfig.for_domain(example.domain)
    rewards: list[float] = []
    for candidate in example.candidates:
        if method == "turing":
            score = turing_likert(
                candidate.text,
                example.ground_truth,
                example.history_profile,
            )
            rewards.append(
                combine_turing_reward(
                    score,
                    candidate.text,
                    example.ground_truth,
                    config,
                )
            )
        elif method == "sim":
            rewards.append(similarity_score(candidate.text, example.ground_truth))
        elif method == "logprob":
            rewards.append(mean_gt_logprob(candidate.text, example.ground_truth))
        else:
            raise ValueError(f"Unknown method: {method}")
    return rewards


def _prob_for_kind(example: Example, probabilities: list[float], kind: str) -> float:
    for index, candidate in enumerate(example.candidates):
        if candidate.kind == kind:
            return probabilities[index]
    raise KeyError(kind)


def evaluate_policy(
    example: Example, logits: list[float], method: str
) -> dict[str, Any]:
    probabilities = softmax(logits)
    rewards = candidate_rewards(example, method)
    expected = sum(
        probability * reward
        for probability, reward in zip(probabilities, rewards, strict=True)
    )
    best_index = max(range(len(probabilities)), key=lambda index: probabilities[index])
    return {
        "probabilities": probabilities,
        "expected_reward": expected,
        "mode_action": example.candidates[best_index].id,
        "mode_label": example.candidates[best_index].label,
        "mode_kind": example.candidates[best_index].kind,
        "human_like_prob": _prob_for_kind(example, probabilities, "human_like"),
        "content_match_prob": _prob_for_kind(example, probabilities, "content_match"),
        "assistant_like_prob": _prob_for_kind(example, probabilities, "assistant_like"),
    }


def train_example(example: Example, method: str, rng: random.Random) -> dict[str, Any]:
    n_actions = len(example.candidates)
    logits = [0.0] * n_actions
    reference = list(logits)
    rewards = candidate_rewards(example, method)
    curve: list[dict[str, float]] = []
    for step in range(STEPS):
        probabilities = softmax(logits)
        actions = sample_actions(probabilities, GROUP_SIZE, rng)
        sampled_rewards = [rewards[action] for action in actions]
        advantages = group_advantages(sampled_rewards)
        logits = update_logits(
            logits,
            actions,
            advantages,
            learning_rate=LEARNING_RATE,
            kl_coefficient=KL_COEFFICIENT,
            reference_logits=reference,
        )
        if step % 10 == 0 or step == STEPS - 1:
            snapshot = evaluate_policy(example, logits, method)
            curve.append(
                {
                    "step": float(step),
                    "expected_reward": float(snapshot["expected_reward"]),
                    "human_like_prob": float(snapshot["human_like_prob"]),
                    "content_match_prob": float(snapshot["content_match_prob"]),
                }
            )
    final = evaluate_policy(example, logits, method)
    scored_candidates = []
    turing_scores = []
    for candidate, reward in zip(example.candidates, rewards, strict=True):
        likert = turing_likert(
            candidate.text, example.ground_truth, example.history_profile
        )
        turing_scores.append(likert)
        scored_candidates.append(
            {
                "id": candidate.id,
                "label": candidate.label,
                "kind": candidate.kind,
                "text": candidate.text,
                "reward": reward,
                "turing_likert": likert,
                "similarity": similarity_score(candidate.text, example.ground_truth),
                "logprob": mean_gt_logprob(candidate.text, example.ground_truth),
            }
        )
    return {
        "example_id": example.example_id,
        "domain": example.domain,
        "user_name": example.user_name,
        "persona": example.persona,
        "history": list(example.history),
        "context": example.context,
        "ground_truth": example.ground_truth,
        "method": method,
        "final": final,
        "curve": curve,
        "candidates": scored_candidates,
        "mean_turing_likert": sum(turing_scores) / len(turing_scores),
    }


def run_mini_replication(seed: int = SEED) -> dict[str, Any]:
    rng = random.Random(seed)
    methods = ("turing", "sim", "logprob")
    runs = []
    summary_rows = []
    for example in get_examples():
        for method in methods:
            result = train_example(example, method, rng)
            runs.append(result)
            summary_rows.append(
                {
                    "example_id": example.example_id,
                    "domain": example.domain,
                    "method": method,
                    "mode_kind": result["final"]["mode_kind"],
                    "human_like_prob": result["final"]["human_like_prob"],
                    "content_match_prob": result["final"]["content_match_prob"],
                    "assistant_like_prob": result["final"]["assistant_like_prob"],
                    "expected_reward": result["final"]["expected_reward"],
                }
            )
    return {
        "paper": {
            "title": "Learning User Simulators with Turing Rewards",
            "arxiv": "2606.19336",
            "openreview_id": "08Z5or1Jys",
            "code": "https://github.com/SusanWYS/turing-rl",
            "human_win_rates": PAPER_HUMAN_WIN_RATES,
            "turing_rl_ablation": PAPER_TURING_RL_ABLATION,
        },
        "replica": {
            "note": (
                "Full GRPO on Qwen3-8B needs about 1680 GPU hours. This replica "
                "keeps the paper's reward formulas and trains a small softmax "
                "policy over dummy replies with a heuristic Turing judge."
            ),
            "group_size": GROUP_SIZE,
            "steps": STEPS,
            "seed": seed,
            "summary": summary_rows,
            "runs": runs,
        },
    }


def write_results(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = run_mini_replication()
    write_results(root / "results" / "mini_replication.json", payload)
    dashboard = root / "dashboard" / "data" / "mini_replication.json"
    write_results(dashboard, payload)


if __name__ == "__main__":
    main()
