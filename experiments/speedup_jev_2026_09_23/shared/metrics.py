"""Classification and latency metrics.

Run from the experiment folder:

    uv run python -c "from shared.metrics import classification_report"
"""

from __future__ import annotations

import numpy as np

from shared.records import PostPrediction, RequestLog

POSITIVE_PROBABILITY_THRESHOLD = 0.5
METRIC_KEYS = ("f1", "accuracy", "precision", "recall")
LATENCY_KEYS = ("p50", "p90", "p99")
PERCENTILE_METHOD = "linear"
ZERO_CLASSIFICATION = {
    "f1": 0.0,
    "accuracy": 0.0,
    "precision": 0.0,
    "recall": 0.0,
}
ZERO_LATENCY = {"p50": 0.0, "p90": 0.0, "p99": 0.0}


def binary_label_from_probability(probability: float) -> int:
    """Return 1 when probability is at least 0.5."""
    if probability >= POSITIVE_PROBABILITY_THRESHOLD:
        return 1
    return 0


def classification_report(gold: list[int], pred: list[int]) -> dict[str, float]:
    """Return f1, accuracy, precision, and recall for positive class 1.

    Parameters
    ----------
    gold
        Gold labels, 0 or 1.
    pred
        Predicted labels, 0 or 1, in the same order as ``gold``.

    Returns
    -------
    dict[str, float]
        Keys ``f1``, ``accuracy``, ``precision``, ``recall``.

    Raises
    ------
    ValueError
        When the two lists differ in length.
    """
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same length")
    pairs = list(zip(gold, pred, strict=True))
    true_positive = sum(1 for g, p in pairs if g == 1 and p == 1)
    false_positive = sum(1 for g, p in pairs if g == 0 and p == 1)
    false_negative = sum(1 for g, p in pairs if g == 1 and p == 0)
    true_negative = len(pairs) - true_positive - false_positive - false_negative
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall)
    accuracy = _ratio(true_positive + true_negative, len(pairs))
    return {"f1": f1, "accuracy": accuracy, "precision": precision, "recall": recall}


def _ratio(numerator: float, denominator: float) -> float:
    """Return ``numerator / denominator``, or 0.0 when the denominator is zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def latency_percentiles(latency_ms: list[float]) -> dict[str, float]:
    """Return p50, p90, and p99 using NumPy percentile method='linear'."""
    values = np.asarray(latency_ms, dtype=float)
    return {
        "p50": float(np.percentile(values, 50, method=PERCENTILE_METHOD)),
        "p90": float(np.percentile(values, 90, method=PERCENTILE_METHOD)),
        "p99": float(np.percentile(values, 99, method=PERCENTILE_METHOD)),
    }


def summarize_pass_predictions(predictions: list[PostPrediction]) -> dict[str, float]:
    """Return classification metrics and per-post latency p50."""
    if not predictions:
        return {**ZERO_CLASSIFICATION, "per_post_latency_ms_p50": 0.0}
    gold = [prediction.gold_label for prediction in predictions]
    pred = [prediction.binary_label for prediction in predictions]
    report = classification_report(gold, pred)
    per_post_latencies = [prediction.per_post_latency_ms for prediction in predictions]
    per_post_p50 = latency_percentiles(per_post_latencies)["p50"]
    return {**report, "per_post_latency_ms_p50": per_post_p50}


def agreement_rate(a: list[int], b: list[int]) -> float:
    """Return the fraction of positions where ``a`` and ``b`` match.

    Parameters
    ----------
    a
        First binary label list.
    b
        Second binary label list.

    Returns
    -------
    float
        Agreement rate in ``[0, 1]``.

    Raises
    ------
    ValueError
        When the two lists differ in length.
    """
    if len(a) != len(b):
        raise ValueError("a and b must have the same length")
    if not a:
        return 0.0
    matches = sum(1 for left, right in zip(a, b, strict=True) if left == right)
    return matches / len(a)


def mean_absolute_difference(a: list[float], b: list[float]) -> float:
    """Return the mean absolute difference between paired floats.

    Parameters
    ----------
    a
        First value list.
    b
        Second value list.

    Returns
    -------
    float
        Mean absolute difference.

    Raises
    ------
    ValueError
        When the two lists differ in length.
    """
    if len(a) != len(b):
        raise ValueError("a and b must have the same length")
    if not a:
        return 0.0
    total = sum(abs(left - right) for left, right in zip(a, b, strict=True))
    return total / len(a)


def summarize_pass_requests(requests: list[RequestLog]) -> dict[str, object]:
    """Return request latency percentiles and token aggregates."""
    if not requests:
        return {
            "request_latency_ms": ZERO_LATENCY,
            "n_requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": 0.0,
            "model_versions": [],
        }
    latencies = [request.request_latency_ms for request in requests]
    model_versions = sorted({request.model_version for request in requests})
    return {
        "request_latency_ms": latency_percentiles(latencies),
        "n_requests": len(requests),
        "input_tokens": sum(request.input_tokens for request in requests),
        "output_tokens": sum(request.output_tokens for request in requests),
        "estimated_cost_usd": sum(request.estimated_cost_usd for request in requests),
        "model_versions": model_versions,
    }
