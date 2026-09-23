"""Classification and latency metrics.

Run from the experiment folder:

    uv run python -c "from shared.metrics import classification_report; print(classification_report([1, 0], [1, 1]))"
"""

POSITIVE_PROBABILITY_THRESHOLD = 0.5
METRIC_KEYS = ("f1", "accuracy", "precision", "recall")
LATENCY_KEYS = ("p50", "p90", "p99")
PERCENTILE_METHOD = "linear"


def binary_label_from_probability(probability: float) -> int:
    """Return 1 when probability is at least 0.5."""
    raise NotImplementedError


def classification_report(gold: list[int], pred: list[int]) -> dict[str, float]:
    """Return f1, accuracy, precision, and recall for positive class 1."""
    raise NotImplementedError


def latency_percentiles(latency_ms: list[float]) -> dict[str, float]:
    """Return p50, p90, and p99 using NumPy percentile method='linear'."""
    raise NotImplementedError
