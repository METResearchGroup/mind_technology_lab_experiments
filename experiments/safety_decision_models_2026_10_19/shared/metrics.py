"""Harness primary metrics aligned with jev-benchmarking (Deußer et al.)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.records import ExampleRecord, PredictionRecord

OPENAI_MOD_HEADS = ("S", "H", "V", "HR", "SH", "S3", "H2", "V2")
POINT_TOLERANCE = 0.02


@dataclass(frozen=True)
class HarnessSpec:
    """Published harness check for one primary metric."""

    dataset: str
    metric_name: str
    published: float
    interval_low: float | None
    interval_high: float | None
    point_only: bool = False


HARNESS_SPECS: tuple[HarnessSpec, ...] = (
    HarnessSpec("toxigen", "accuracy", 0.878, 0.857, 0.898),
    HarnessSpec("openai_moderation", "mean_auprc", 0.717, 0.675, 0.759),
    HarnessSpec("toxicchat", "toxic_f1", 0.786, None, None, point_only=True),
    HarnessSpec("toxicchat", "jailbreak_f1", 0.717, None, None, point_only=True),
    HarnessSpec("prompt_injections", "accuracy", 0.741, 0.664, 0.828),
    HarnessSpec("go_emotions", "macro_f1", 0.243, None, None, point_only=True),
    HarnessSpec("emotion", "accuracy", 0.585, 0.563, 0.605),
)


def answers_map(prediction: PredictionRecord) -> dict[str, dict[str, Any]]:
    raw = prediction.raw_response or {}
    answers = raw.get("answers", {})
    if not isinstance(answers, dict):
        return {}
    return {str(key): normalize_answer(value) for key, value in answers.items()}


def normalize_answer(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def noul_value(answer: dict[str, Any]) -> float | None:
    if answer.get("type") == "noul" or "noul" in answer:
        noul = answer.get("noul")
        return float(noul) if noul is not None else None
    return None


def choice_value(answer: dict[str, Any]) -> str | None:
    choice = answer.get("choice")
    if choice is None:
        return None
    return str(choice)


def binary_accuracy(
    golds: list[bool], answers: list[dict[str, Any]], threshold: float
) -> float:
    hits = 0
    for gold, answer in zip(golds, answers, strict=True):
        prob = float(answer["noul"])
        pred = prob >= threshold
        if pred == gold:
            hits += 1
    return hits / len(golds)


def binary_f1(
    golds: list[bool], answers: list[dict[str, Any]], threshold: float
) -> float:
    tp = fp = fn = 0
    for gold, answer in zip(golds, answers, strict=True):
        prob = float(answer["noul"])
        pred = prob >= threshold
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif not pred and gold:
            fn += 1
    denom = 2 * tp + fp + fn
    return (2 * tp / denom) if denom else 0.0


def macro_f1_multilabel(
    gold_matrix: list[list[int]],
    prob_matrix: list[list[float]],
    threshold: float,
) -> float:
    if not gold_matrix:
        return math.nan
    n_labels = len(gold_matrix[0])
    f1s: list[float] = []
    for j in range(n_labels):
        tp = fp = fn = 0
        for gold_row, prob_row in zip(gold_matrix, prob_matrix, strict=True):
            gold = gold_row[j] == 1
            pred = prob_row[j] >= threshold
            if pred and gold:
                tp += 1
            elif pred and not gold:
                fp += 1
            elif not pred and gold:
                fn += 1
        denom = 2 * tp + fp + fn
        f1s.append((2 * tp / denom) if denom else 0.0)
    return sum(f1s) / len(f1s)


def average_precision(golds: list[bool], scores: list[float]) -> float:
    if not golds:
        return math.nan
    positives = sum(1 for gold in golds if gold)
    if positives == 0:
        return 0.0
    ordered = sorted(zip(scores, golds), key=lambda pair: pair[0], reverse=True)
    tp = 0
    precisions: list[float] = []
    for rank, (_, gold) in enumerate(ordered, start=1):
        if gold:
            tp += 1
            precisions.append(tp / rank)
    return sum(precisions) / positives if precisions else 0.0


def compute_dataset_metrics(
    dataset: str,
    rows: list[ExampleRecord],
    preds: list[PredictionRecord],
    *,
    threshold: float,
    template_path: Path | None = None,
) -> dict[str, float]:
    """Return primary harness metrics for one dataset."""
    if dataset == "toxigen":
        golds: list[bool] = []
        answers: list[dict[str, Any]] = []
        for row, pred in zip(rows, preds, strict=True):
            ans = answers_map(pred).get("toxic")
            if ans is None or noul_value(ans) is None:
                raise ValueError("toxigen prediction missing toxic noul head")
            golds.append(bool(row.gold_labels["toxic"]))  # type: ignore[index]
            answers.append({"noul": noul_value(ans)})
        return {"accuracy": binary_accuracy(golds, answers, threshold)}

    if dataset == "openai_moderation":
        auprcs: list[float] = []
        for head in OPENAI_MOD_HEADS:
            golds = []
            scores = []
            for row, pred in zip(rows, preds, strict=True):
                golds.append(bool(row.gold_labels.get(head, False)))  # type: ignore[union-attr]
                ans = answers_map(pred).get(head)
                if ans is None or noul_value(ans) is None:
                    raise ValueError(f"openai_moderation missing noul for head {head}")
                scores.append(float(noul_value(ans)))
            auprcs.append(average_precision(golds, scores))
        return {"mean_auprc": sum(auprcs) / len(auprcs)}

    if dataset == "toxicchat":
        out: dict[str, float] = {}
        for head, key in (("toxic", "toxic_f1"), ("jailbreak", "jailbreak_f1")):
            golds = []
            answers = []
            for row, pred in zip(rows, preds, strict=True):
                ans = answers_map(pred).get(head)
                if ans is None or noul_value(ans) is None:
                    raise ValueError(f"toxicchat missing noul head {head}")
                golds.append(bool(row.gold_labels[head]))  # type: ignore[index]
                answers.append({"noul": noul_value(ans)})
            out[key] = binary_f1(golds, answers, threshold)
        return out

    if dataset == "prompt_injections":
        golds = []
        answers = []
        for row, pred in zip(rows, preds, strict=True):
            ans = answers_map(pred).get("answer")
            if ans is None or noul_value(ans) is None:
                raise ValueError("prompt_injections missing answer noul head")
            golds.append(bool(row.gold_labels["answer"]))  # type: ignore[index]
            answers.append({"noul": noul_value(ans)})
        return {"accuracy": binary_accuracy(golds, answers, threshold)}

    if dataset == "go_emotions":
        if template_path is None:
            raise ValueError("go_emotions metrics require template_path")
        label_names = sorted(json.loads(template_path.read_text(encoding="utf-8")).keys())
        gold_matrix: list[list[int]] = []
        prob_matrix: list[list[float]] = []
        for row, pred in zip(rows, preds, strict=True):
            answers = answers_map(pred)
            gold_matrix.append(
                [
                    1 if row.gold_labels.get(label, False) else 0  # type: ignore[union-attr]
                    for label in label_names
                ]
            )
            prob_matrix.append(
                [float(noul_value(answers[label]) or 0.0) for label in label_names]
            )
        return {
            "macro_f1": macro_f1_multilabel(gold_matrix, prob_matrix, threshold)
        }

    if dataset == "emotion":
        correct = 0
        for row, pred in zip(rows, preds, strict=True):
            ans = answers_map(pred).get("answer")
            if ans is None or choice_value(ans) is None:
                raise ValueError("emotion missing choice answer head")
            if choice_value(ans) == row.gold_labels:
                correct += 1
        return {"accuracy": correct / len(rows) if rows else math.nan}

    raise ValueError(f"unknown harness dataset {dataset}")


def check_harness_value(spec: HarnessSpec, observed: float) -> bool:
    if spec.point_only:
        return abs(observed - spec.published) <= POINT_TOLERANCE
    if spec.interval_low is None or spec.interval_high is None:
        return abs(observed - spec.published) <= POINT_TOLERANCE
    return spec.interval_low <= observed <= spec.interval_high


def format_interval(spec: HarnessSpec) -> str:
    if spec.point_only:
        return f"±{POINT_TOLERANCE}"
    if spec.interval_low is not None and spec.interval_high is not None:
        return f"{spec.interval_low:.3f}-{spec.interval_high:.3f}"
    return "—"
