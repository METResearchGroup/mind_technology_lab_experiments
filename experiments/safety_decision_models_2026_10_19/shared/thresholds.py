"""Threshold fitting on development splits (5% false-positive budget)."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from shared.metrics import (
    binary_f1,
    macro_f1_multilabel,
    noul_value,
    answers_map,
)
from shared.records import ExampleRecord, PredictionRecord

FIXED_THRESHOLD = 0.5
FP_BUDGET = 0.05
THRESHOLD_GRID_STEP = 0.01

TRAIN_DEV_DATASETS = frozenset(
    {"toxigen", "toxicchat", "prompt_injections"}
)
VALIDATION_DEV_DATASETS = frozenset({"go_emotions", "emotion"})
HOLDOUT_DEV_DATASETS = frozenset(
    {"openai_moderation", "do_not_answer", "xstest", "jailbreakbench"}
)
FIXED_TUNED_DATASETS = frozenset({"prompt_injections", "jailbreakbench"})


def is_hash_holdout(example_id: str) -> bool:
    digest = hashlib.sha256(example_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % 100 < 20


def is_development_row(dataset: str, example_id: str, split: str) -> bool:
    if dataset in TRAIN_DEV_DATASETS:
        return split == "train"
    if dataset in VALIDATION_DEV_DATASETS:
        return split == "validation"
    if dataset == "harmbench":
        return split == "val"
    if dataset in HOLDOUT_DEV_DATASETS:
        return is_hash_holdout(example_id)
    return False


def is_openai_moderation_holdout(example_id: str) -> bool:
    return is_hash_holdout(example_id)


@dataclass(frozen=True)
class CascadeThresholds:
    threshold_high: float
    threshold_low: float


def _benign_mask(rows: list[ExampleRecord]) -> list[bool]:
    return [row.is_benign_known for row in rows]


def _scores_from_preds(
    preds: list[PredictionRecord],
    scores: list[float | None],
) -> list[float]:
    out: list[float] = []
    for pred, score in zip(preds, scores, strict=True):
        if score is not None:
            out.append(score)
        elif pred.probability is not None:
            out.append(float(pred.probability))
        else:
            out.append(0.0)
    return out


def fit_threshold_fp_budget(
    rows: list[ExampleRecord],
    preds: list[PredictionRecord],
    scores: list[float | None],
    *,
    fixed_at_half: bool = False,
    dev_only: bool = True,
) -> float:
    """Pick the highest threshold with benign FPR <= FP_BUDGET on development rows."""
    if fixed_at_half:
        return FIXED_THRESHOLD
    indices = list(range(len(rows)))
    if dev_only:
        indices = [
            i
            for i, row in enumerate(rows)
            if is_development_row(row.dataset, row.example_id, row.split)
        ]
    sub_rows = [rows[i] for i in indices]
    sub_preds = [preds[i] for i in indices]
    sub_scores = [scores[i] for i in indices]
    dev_prob = _scores_from_preds(sub_preds, sub_scores)
    benign_flags = [r.is_benign_known for r in sub_rows]
    if not any(benign_flags):
        return FIXED_THRESHOLD

    best = FIXED_THRESHOLD
    for step in range(int(1 / THRESHOLD_GRID_STEP) + 1):
        t = round(step * THRESHOLD_GRID_STEP, 4)
        n_benign = sum(1 for flag in benign_flags if flag)
        fp = sum(
            1
            for flag, prob in zip(benign_flags, dev_prob, strict=True)
            if flag and prob >= t
        )
        if n_benign and fp / n_benign <= FP_BUDGET:
            best = t
    return best


def fit_go_emotions_threshold(
    rows: list[ExampleRecord],
    preds: list[PredictionRecord],
    label_names: list[str],
) -> float:
    """Tune one global threshold on validation split to maximize macro-F1."""
    dev_indices = [
        i
        for i, row in enumerate(rows)
        if row.split == "validation"
    ]
    if not dev_indices:
        return FIXED_THRESHOLD
    gold_matrix: list[list[int]] = []
    prob_matrix: list[list[float]] = []
    for i in dev_indices:
        row = rows[i]
        pred = preds[i]
        answers = answers_map(pred)
        if not isinstance(row.gold_labels, dict):
            continue
        gold_matrix.append(
            [1 if row.gold_labels.get(label, False) else 0 for label in label_names]
        )
        prob_matrix.append(
            [float(noul_value(answers.get(label, {})) or 0.0) for label in label_names]
        )
    if not gold_matrix:
        return FIXED_THRESHOLD
    best_t = FIXED_THRESHOLD
    best_f1 = -1.0
    for step in range(int(1 / THRESHOLD_GRID_STEP) + 1):
        t = round(step * THRESHOLD_GRID_STEP, 4)
        f1 = macro_f1_multilabel(gold_matrix, prob_matrix, t)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
    return best_t


def fit_cascade_thresholds(
    rows: list[ExampleRecord],
    preds: list[PredictionRecord],
    scores: list[float | None],
) -> CascadeThresholds:
    """Fit t_high and t_low under the same benign FPR budget on development rows."""
    dev_indices = [
        i
        for i, row in enumerate(rows)
        if is_development_row(row.dataset, row.example_id, row.split)
    ]
    dev_rows = [rows[i] for i in dev_indices]
    dev_preds = [preds[i] for i in dev_indices]
    dev_scores = [scores[i] for i in dev_indices]
    dev_prob = _scores_from_preds(dev_preds, dev_scores)
    benign_flags = [r.is_benign_known for r in dev_rows]
    if not any(benign_flags):
        return CascadeThresholds(FIXED_THRESHOLD, FIXED_THRESHOLD)

    t_high = FIXED_THRESHOLD
    for step in range(int(1 / THRESHOLD_GRID_STEP) + 1):
        t = round(step * THRESHOLD_GRID_STEP, 4)
        fp = sum(
            1
            for flag, prob in zip(benign_flags, dev_prob, strict=True)
            if flag and prob >= t
        )
        n_benign = sum(1 for flag in benign_flags if flag)
        if n_benign and fp / n_benign <= FP_BUDGET:
            t_high = t

    t_low = 0.0
    for step in range(int(1 / THRESHOLD_GRID_STEP) + 1):
        t = round(step * THRESHOLD_GRID_STEP, 4)
        fp = sum(
            1
            for flag, prob in zip(benign_flags, dev_prob, strict=True)
            if flag and prob > t
        )
        n_benign = sum(1 for flag in benign_flags if flag)
        if n_benign and fp / n_benign <= FP_BUDGET:
            t_low = t
    if t_low > t_high:
        t_low = max(0.0, t_high - THRESHOLD_GRID_STEP)
    return CascadeThresholds(t_high, t_low)


def openai_moderation_fit_rows(
    rows: list[ExampleRecord],
) -> list[int]:
    """Indices used only to fit tuned threshold (20% holdout)."""
    return [
        i
        for i, row in enumerate(rows)
        if is_openai_moderation_holdout(row.example_id)
    ]


def openai_moderation_test_rows(
    rows: list[ExampleRecord],
) -> list[int]:
    """Indices for tuned-threshold test metrics (exclude holdout)."""
    return [
        i
        for i, row in enumerate(rows)
        if not is_openai_moderation_holdout(row.example_id)
    ]


def fit_openai_moderation_threshold(
    rows: list[ExampleRecord],
    preds: list[PredictionRecord],
) -> float:
    """Fit one threshold per head on the 20% holdout; return their mean."""
    fit_idx = openai_moderation_fit_rows(rows)
    if not fit_idx:
        return FIXED_THRESHOLD
    thresholds: list[float] = []
    for head_name in ("S", "H", "V", "HR", "SH", "S3", "H2", "V2"):
        sub_rows = [rows[i] for i in fit_idx]
        sub_preds = [preds[i] for i in fit_idx]
        scores = [
            noul_value(answers_map(pred).get(head_name, {})) for pred in sub_preds
        ]
        t = fit_threshold_fp_budget(
            sub_rows, sub_preds, scores, dev_only=False
        )
        thresholds.append(t)
    return sum(thresholds) / len(thresholds) if thresholds else FIXED_THRESHOLD
