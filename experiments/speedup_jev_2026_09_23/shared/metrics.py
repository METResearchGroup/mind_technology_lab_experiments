"""Classification and latency metrics.

Run from the experiment folder:

    uv run python -c "from shared.metrics import classification_report; print(classification_report([1, 0], [1, 1]))"
"""

import numpy as np

POSITIVE_PROBABILITY_THRESHOLD = 0.5
METRIC_KEYS = ("f1", "accuracy", "precision", "recall")
LATENCY_KEYS = ("p50", "p90", "p99")
PERCENTILE_METHOD = "linear"


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
