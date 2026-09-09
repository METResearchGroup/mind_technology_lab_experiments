"""Minimal PRISK replication: factorial personalization-risk evaluation."""

from prisk.evaluate import run_replication
from prisk.metrics import (
    coverage_rate,
    irp_score,
    normalize_1_to_5,
    personalization_induced_sycophancy,
    relative_coverage,
    sycophancy_score,
    useful_item_recall,
)

__all__ = [
    "coverage_rate",
    "irp_score",
    "normalize_1_to_5",
    "personalization_induced_sycophancy",
    "relative_coverage",
    "run_replication",
    "sycophancy_score",
    "useful_item_recall",
]
