"""Classification and latency metrics shared by every scorer.

Run from the experiment folder:

    uv run python -c "from shared.metrics import classification_report; print(classification_report.__name__)"
"""

from shared.records import POSITIVE_PROBABILITY_THRESHOLD

METRIC_KEYS = ("f1", "accuracy", "precision", "recall")
LATENCY_KEYS = ("p50", "p90", "p99")
DIFFERENCE_KEYS = ("mean", "median", "std", "iqr")
PERCENTILE_METHOD = "linear"


def binary_label_from_probability(probability: float) -> int:
    """Return 1 when probability is at least 0.5."""
    if probability >= POSITIVE_PROBABILITY_THRESHOLD:
        return 1
    return 0


def classification_report(gold: list[int], pred: list[int]) -> dict[str, float]:
    """Return f1, accuracy, precision, and recall for positive class 1."""
    if len(gold) != len(pred):
        raise ValueError("gold and pred must have the same length")
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    for gold_label, pred_label in zip(gold, pred, strict=True):
        if gold_label == 1 and pred_label == 1:
            true_positive += 1
        elif gold_label == 0 and pred_label == 1:
            false_positive += 1
        elif gold_label == 1 and pred_label == 0:
            false_negative += 1
        else:
            true_negative += 1
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = _ratio(2 * precision * recall, precision + recall)
    accuracy = _ratio(
        true_positive + true_negative,
        true_positive + true_negative + false_positive + false_negative,
    )
    return {"f1": f1, "accuracy": accuracy, "precision": precision, "recall": recall}


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def latency_percentiles(latency_ms: list[float]) -> dict[str, float]:
    """Return p50, p90, and p99 using NumPy linear percentile."""
    raise NotImplementedError


def paired_difference_summary(
    jev: list[float], perspective: list[float]
) -> dict[str, float]:
    """Return mean, median, std, and iqr of jev minus perspective."""
    raise NotImplementedError
