from __future__ import annotations

import math
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

import numpy as np

from lifemem.types import GenerationRecord

EPS = 1e-9


def _labels(records: list[GenerationRecord]) -> list[str]:
    for record in records:
        if record.valid_options:
            return list(record.valid_options)
    return []


def _keep(values: list[str | None], labels: list[str]) -> list[str]:
    allowed = set(labels)
    return [
        str(value) for value in values if value is not None and str(value) in allowed
    ]


def _dist(values: list[str], labels: list[str]) -> np.ndarray:
    counts = Counter(values)
    arr = np.asarray([counts.get(label, 0) for label in labels], dtype=np.float64) + EPS
    return arr / arr.sum()


def normalized_entropy(prob: np.ndarray) -> float:
    if len(prob) <= 1:
        return 0.0
    return float(-(prob * np.log(prob)).sum() / math.log(len(prob)))


def kl_divergence(human: np.ndarray, model: np.ndarray) -> float:
    return float((human * np.log(human / model)).sum())


def js_divergence(a: np.ndarray, b: np.ndarray) -> float:
    mix = 0.5 * (a + b)
    return float(0.5 * (a * np.log(a / mix)).sum() + 0.5 * (b * np.log(b / mix)).sum())


def pairwise_categorical_distance(values: list[str]) -> float | None:
    n = len(values)
    if n < 2:
        return None
    same = sum(count * (count - 1) for count in Counter(values).values())
    return float(1.0 - same / (n * (n - 1)))


def distribution_metrics(records: list[GenerationRecord]) -> dict[str, Any]:
    by_cell: dict[tuple[int, str], list[GenerationRecord]] = defaultdict(list)
    for record in records:
        by_cell[(record.wave, record.variable)].append(record)
    kls: list[float] = []
    entropy_gaps: list[float] = []
    cells: dict[str, dict[str, Any]] = {}
    for (wave, variable), rows in sorted(by_cell.items()):
        labels = _labels(rows)
        if not labels:
            continue
        human = _keep([row.human_answer for row in rows], labels)
        model = _keep([row.parsed_answer for row in rows], labels)
        if not human or not model:
            continue
        p_h = _dist(human, labels)
        p_m = _dist(model, labels)
        kl = kl_divergence(p_h, p_m)
        gap = abs(normalized_entropy(p_m) - normalized_entropy(p_h))
        kls.append(kl)
        entropy_gaps.append(gap)
        cells[f"w{wave}:{variable}"] = {
            "kl": kl,
            "entropy_gap": gap,
            "js": js_divergence(p_h, p_m),
        }
    return {
        "kl": float(np.mean(kls)) if kls else None,
        "entropy_gap": float(np.mean(entropy_gaps)) if entropy_gaps else None,
        "num_cells": len(kls),
        "cells": cells,
    }


def within_group_pairwise_gap(
    records: list[GenerationRecord],
    group_variables: tuple[str, ...],
    min_group_size: int = 2,
) -> dict[str, Any]:
    by_question: dict[tuple[int, str], list[GenerationRecord]] = defaultdict(list)
    for record in records:
        by_question[(record.wave, record.variable)].append(record)
    gaps: list[float] = []
    human_d: list[float] = []
    model_d: list[float] = []
    for rows in by_question.values():
        labels = _labels(rows)
        if not labels:
            continue
        for group_var in group_variables:
            grouped: dict[str, list[GenerationRecord]] = defaultdict(list)
            for row in rows:
                value = row.identity_groups.get(group_var)
                if value:
                    grouped[value].append(row)
            for group_rows in grouped.values():
                if len(group_rows) < min_group_size:
                    continue
                human = _keep([row.human_answer for row in group_rows], labels)
                model = _keep([row.parsed_answer for row in group_rows], labels)
                d_h = pairwise_categorical_distance(human)
                d_m = pairwise_categorical_distance(model)
                if d_h is None or d_m is None:
                    continue
                human_d.append(d_h)
                model_d.append(d_m)
                gaps.append(abs(d_m - d_h))
    return {
        "wg_gap": float(np.mean(gaps)) if gaps else None,
        "human_mean_wg_distance": float(np.mean(human_d)) if human_d else None,
        "model_mean_wg_distance": float(np.mean(model_d)) if model_d else None,
        "num_cells": len(gaps),
    }


def transition_js(records: list[GenerationRecord]) -> dict[str, Any]:
    by_key: dict[tuple[str, str], list[GenerationRecord]] = defaultdict(list)
    for record in records:
        by_key[(record.agent_id, record.variable)].append(record)
    human_by_q: dict[str, list[str]] = defaultdict(list)
    model_by_q: dict[str, list[str]] = defaultdict(list)
    labels_by_q: dict[str, set[str]] = defaultdict(set)
    for (_agent, variable), rows in by_key.items():
        ordered = sorted(rows, key=lambda item: item.wave)
        for prev, curr in zip(ordered, ordered[1:], strict=False):
            labels = list(curr.valid_options)
            if (
                prev.human_answer not in labels
                or curr.human_answer not in labels
                or prev.parsed_answer not in labels
                or curr.parsed_answer not in labels
            ):
                continue
            h = f"{prev.human_answer}->{curr.human_answer}"
            m = f"{prev.parsed_answer}->{curr.parsed_answer}"
            human_by_q[variable].append(h)
            model_by_q[variable].append(m)
            labels_by_q[variable].update({h, m})
    values: list[float] = []
    for variable, labels in labels_by_q.items():
        value = js_divergence(
            _dist(human_by_q[variable], sorted(labels)),
            _dist(model_by_q[variable], sorted(labels)),
        )
        values.append(value)
    return {
        "transition_js": float(np.mean(values)) if values else None,
        "num_questions": len(values),
    }


def silhouette(matrix: np.ndarray, labels: list[str]) -> float:
    if matrix.shape[0] < 2:
        return 0.0
    scores: list[float] = []
    for i, label in enumerate(labels):
        same = [j for j, other in enumerate(labels) if other == label and j != i]
        other_groups = {other for other in labels if other != label}
        if not same or not other_groups:
            continue
        a = float(np.mean([np.linalg.norm(matrix[i] - matrix[j]) for j in same]))
        b = min(
            float(
                np.mean(
                    [
                        np.linalg.norm(matrix[i] - matrix[j])
                        for j, other in enumerate(labels)
                        if other == group
                    ]
                )
            )
            for group in other_groups
        )
        denom = max(a, b)
        scores.append(0.0 if denom == 0 else (b - a) / denom)
    return float(np.mean(scores)) if scores else 0.0


def response_matrix(
    records: list[GenerationRecord],
    field: str,
) -> tuple[np.ndarray, list[str], list[str]]:
    agents = sorted({record.agent_id for record in records})
    variables = sorted({record.variable for record in records})
    lookup: dict[tuple[str, str], str] = {}
    identity: dict[str, str] = {}
    codes = sorted({code for record in records for code in record.valid_options})
    code_index = {code: idx for idx, code in enumerate(codes)}
    for record in records:
        value = getattr(record, field)
        if value is None:
            continue
        lookup[(record.agent_id, record.variable)] = str(value)
        identity[record.agent_id] = record.identity_groups.get("ses", "unknown")
    rows: list[list[float]] = []
    kept_ids: list[str] = []
    groups: list[str] = []
    width = len(variables) * max(len(codes), 1)
    for agent in agents:
        vec = np.zeros(width, dtype=np.float64)
        filled = False
        for q_idx, variable in enumerate(variables):
            value = lookup.get((agent, variable))
            if value is None or value not in code_index:
                continue
            vec[q_idx * len(codes) + code_index[value]] = 1.0
            filled = True
        if not filled:
            continue
        rows.append(vec.tolist())
        kept_ids.append(agent)
        groups.append(identity.get(agent, "unknown"))
    matrix = np.asarray(rows, dtype=np.float64)
    if matrix.size:
        std = matrix.std(axis=0)
        std[std == 0] = 1.0
        matrix = (matrix - matrix.mean(axis=0)) / std
    return matrix, kept_ids, groups


def pca_2d(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return np.zeros((0, 2))
    centered = matrix - matrix.mean(axis=0)
    _u, _s, vt = np.linalg.svd(centered, full_matrices=False)
    components = vt[:2].T
    if components.shape[1] == 1:
        components = np.hstack([components, np.zeros((components.shape[0], 1))])
    return centered @ components[:, :2]


def summarize_method(
    records: list[GenerationRecord],
    group_variables: tuple[str, ...],
) -> dict[str, Any]:
    dist = distribution_metrics(records)
    wg = within_group_pairwise_gap(records, group_variables)
    trans = transition_js(records)
    return {
        "kl": dist["kl"],
        "wg_gap": wg["wg_gap"],
        "entropy_gap": dist["entropy_gap"],
        "transition_js": trans["transition_js"],
        "distribution": dist,
        "within_group": wg,
        "transitions": trans,
        "n_records": len(records),
    }


def pairwise_distance_mae(records: list[GenerationRecord]) -> float | None:
    by_agent: dict[str, dict[str, tuple[str | None, str | None]]] = defaultdict(dict)
    for record in records:
        by_agent[record.agent_id][record.variable] = (
            record.human_answer,
            record.parsed_answer,
        )
    human_d: list[float] = []
    model_d: list[float] = []
    for a, b in combinations(sorted(by_agent), 2):
        shared = sorted(set(by_agent[a]) & set(by_agent[b]))
        h_dist = 0
        p_dist = 0
        dim = 0
        for var in shared:
            ha, pa = by_agent[a][var]
            hb, pb = by_agent[b][var]
            if None in {ha, pa, hb, pb}:
                continue
            dim += 1
            h_dist += str(ha) != str(hb)
            p_dist += str(pa) != str(pb)
        if dim:
            human_d.append(h_dist / dim)
            model_d.append(p_dist / dim)
    if not human_d:
        return None
    return float(np.mean(np.abs(np.asarray(human_d) - np.asarray(model_d))))
