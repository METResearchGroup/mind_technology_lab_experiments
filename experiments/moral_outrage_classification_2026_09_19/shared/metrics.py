"""Classification and latency metrics shared by every scorer.

Run from the experiment folder:

    uv run python -c "from shared.metrics import classification_report; print(classification_report.__name__)"
"""

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
    raise NotImplementedError


def latency_percentiles(latency_ms: list[float]) -> dict[str, float]:
    """Return p50, p90, and p99 using NumPy linear percentile."""
    raise NotImplementedError


def paired_difference_summary(
    jev: list[float], perspective: list[float]
) -> dict[str, float]:
    """Return mean, median, std, and iqr of jev minus perspective."""
    raise NotImplementedError
