"""Write root RESULTS and comparison plot.

Run from the experiment folder:

    uv run python scripts/write_results.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

BATCH_SIZES: tuple[int, ...] = (1, 5, 10, 20, 30, 40)
PR20_ROW_LABEL = "PR 20"


class Pr20Results(BaseModel):
    """Serialized PR 20 Jev metrics."""

    model_name: str
    n_scored: int
    n_missing_label: int
    n_deadletter: int
    f1: float
    accuracy: float
    precision: float
    recall: float
    p50: float
    p90: float
    p99: float
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float


class QualityRow(BaseModel):
    """One quality table row."""

    label: str
    f1: float
    accuracy: float
    precision: float
    recall: float
    scored: int
    deadletter: int


class LatencyRow(BaseModel):
    """One latency table row."""

    label: str
    request_p50_ms: float
    request_p90_ms: float
    request_p99_ms: float
    per_post_p50_ms: float
    wall_time_seconds: str


class CostRow(BaseModel):
    """One cost table row."""

    label: str
    requests: int
    input_tokens: int
    output_tokens: int
    estimated_usd: float
    usd_per_1000_posts: float


class DriftRow(BaseModel):
    """One drift table row."""

    label: str
    agreement: float
    mean_abs_prob_diff: float


def main() -> None:
    """Build comparison tables, plot, and root RESULTS."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
