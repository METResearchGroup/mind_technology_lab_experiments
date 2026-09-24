"""Write root RESULTS and comparison plot.

Run from the experiment folder:

    uv run python scripts/write_results.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from pydantic import BaseModel  # noqa: E402

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from run_batch_size import PassResults  # noqa: E402
from shared.metrics import agreement_rate, mean_absolute_difference  # noqa: E402
from shared.pricing import (  # noqa: E402
    PRICE_PAGE_DATE,
    PRICE_PAGE_URL,
    estimate_jev_cost_usd,
)
from shared.rate_limiter import MAX_REQUEST_STARTS_PER_MINUTE, WINDOW_SECONDS  # noqa: E402
from shared.records import BATCH_SIZES  # noqa: E402

PR20_ROW_LABEL = "PR 20"
PR20_MODEL_NAME = "jev-latest"
TODAY_MODEL_VERSION = "jev-1.13.0"
POSTS_PER_RUN = 1000
METRIC_DECIMALS = 3
MS_DECIMALS = 1
SECONDS_DECIMALS = 1
USD_DECIMALS = 6
ROW_ID_COLUMN = "source_row_id"
BINARY_LABEL_COLUMN = "binary_label"
PROBABILITY_COLUMN = "probability"
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
COMPARISON_DIR = OUTPUTS_DIR / "comparison"
PLOT_FILENAME = "f1_and_latency_by_batch_size.png"
RESULTS_PATH = EXPERIMENT_ROOT / "RESULTS.md"
PR20_RESULTS_PATH = EXPERIMENT_ROOT / "data" / "pr20_jev_results.json"
PR20_LABELS_PATH = EXPERIMENT_ROOT / "data" / "pr20_jev_labels.parquet"
PRICE_SOURCE = f"{PRICE_PAGE_URL} ({PRICE_PAGE_DATE})"
NOTE_BASELINE = (
    "Batch size 1 is today's baseline on "
    f"{TODAY_MODEL_VERSION}. PR 20 used {PR20_MODEL_NAME} with an unrecorded version."
)
NOTE_RATE_LIMIT = (
    f"The request start cap of {MAX_REQUEST_STARTS_PER_MINUTE:,} per minute counts starts "
    f"in a rolling {int(WINDOW_SECONDS)} s window, so it did not throttle any pass "
    "(the batch size 1 pass started 1,000 requests in about 17 s)."
)
NOTE_PR20_WALL_TIME = "Wall time for PR 20 was not recorded."
NOTE_DRIFT = (
    "Drift is measured against today's batch size 1 on posts scored in both runs."
)


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
    pass_results = _load_all_pass_results()
    baseline_labels = _load_batch_labels(1)
    drift_rows = _build_drift_rows(baseline_labels)
    quality_rows = _build_quality_rows(pass_results)
    latency_rows = _build_latency_rows(pass_results)
    cost_rows = _build_cost_rows(pass_results)
    plot_path = _write_comparison_plot(pass_results)
    markdown = _render_results_markdown(
        quality_rows,
        latency_rows,
        cost_rows,
        drift_rows,
        plot_path,
    )
    RESULTS_PATH.write_text(markdown, encoding="utf-8")


def _load_all_pass_results() -> dict[int, PassResults]:
    """Load ``results.json`` for every configured batch size."""
    results: dict[int, PassResults] = {}
    for batch_size in BATCH_SIZES:
        results[batch_size] = _load_pass_results(batch_size)
    return results


def _load_pass_results(batch_size: int) -> PassResults:
    """Load one pass ``results.json`` by batch size."""
    path = OUTPUTS_DIR / f"batch_{batch_size}" / "results.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PassResults.model_validate(payload)


def _load_pr20_results() -> Pr20Results:
    """Load serialized PR 20 Jev metrics from ``data/``."""
    payload = json.loads(PR20_RESULTS_PATH.read_text(encoding="utf-8"))
    return Pr20Results.model_validate(payload)


def _load_batch_labels(batch_size: int) -> pd.DataFrame:
    """Load label columns for one batch-size pass."""
    path = OUTPUTS_DIR / f"batch_{batch_size}" / "labels.parquet"
    frame = pd.read_parquet(path)
    return frame[[ROW_ID_COLUMN, BINARY_LABEL_COLUMN, PROBABILITY_COLUMN]]


def _load_pr20_labels() -> pd.DataFrame:
    """Load PR 20 label columns for drift comparison."""
    frame = pd.read_parquet(PR20_LABELS_PATH)
    return frame[[ROW_ID_COLUMN, BINARY_LABEL_COLUMN, PROBABILITY_COLUMN]]


def _compute_drift(
    baseline_labels: pd.DataFrame,
    other_labels: pd.DataFrame,
) -> tuple[float, float]:
    """Return label agreement and mean absolute probability difference."""
    merged = baseline_labels.merge(
        other_labels,
        on=ROW_ID_COLUMN,
        suffixes=("_baseline", "_other"),
    )
    baseline_binary = merged[f"{BINARY_LABEL_COLUMN}_baseline"].astype(int).tolist()
    other_binary = merged[f"{BINARY_LABEL_COLUMN}_other"].astype(int).tolist()
    baseline_probs = merged[f"{PROBABILITY_COLUMN}_baseline"].astype(float).tolist()
    other_probs = merged[f"{PROBABILITY_COLUMN}_other"].astype(float).tolist()
    agreement = agreement_rate(baseline_binary, other_binary)
    mad = mean_absolute_difference(baseline_probs, other_probs)
    return agreement, mad


def _build_drift_rows(baseline_labels: pd.DataFrame) -> list[DriftRow]:
    """Build drift table rows against batch size 1."""
    rows: list[DriftRow] = []
    for batch_size in BATCH_SIZES:
        labels = _load_batch_labels(batch_size)
        agreement, mad = _compute_drift(baseline_labels, labels)
        rows.append(
            DriftRow(
                label=str(batch_size),
                agreement=agreement,
                mean_abs_prob_diff=mad,
            )
        )
    pr20_labels = _load_pr20_labels()
    agreement, mad = _compute_drift(baseline_labels, pr20_labels)
    rows.append(
        DriftRow(
            label=PR20_ROW_LABEL,
            agreement=agreement,
            mean_abs_prob_diff=mad,
        )
    )
    return rows


def _build_quality_rows(pass_results: dict[int, PassResults]) -> list[QualityRow]:
    """Build quality metrics rows for all batch sizes and PR 20."""
    rows = [
        _quality_row_from_pass(str(batch_size), pass_results[batch_size])
        for batch_size in BATCH_SIZES
    ]
    rows.append(_quality_row_from_pr20(_load_pr20_results()))
    return rows


def _quality_row_from_pass(label: str, results: PassResults) -> QualityRow:
    """Map one pass ``PassResults`` to a quality table row."""
    return QualityRow(
        label=label,
        f1=results.f1,
        accuracy=results.accuracy,
        precision=results.precision,
        recall=results.recall,
        scored=results.n_scored,
        deadletter=results.n_deadletter,
    )


def _quality_row_from_pr20(results: Pr20Results) -> QualityRow:
    """Map PR 20 metrics to a quality table row."""
    return QualityRow(
        label=PR20_ROW_LABEL,
        f1=results.f1,
        accuracy=results.accuracy,
        precision=results.precision,
        recall=results.recall,
        scored=results.n_scored,
        deadletter=results.n_deadletter,
    )


def _build_latency_rows(pass_results: dict[int, PassResults]) -> list[LatencyRow]:
    """Build latency table rows for all batch sizes and PR 20."""
    rows = [
        _latency_row_from_pass(str(batch_size), pass_results[batch_size])
        for batch_size in BATCH_SIZES
    ]
    rows.append(_latency_row_from_pr20(_load_pr20_results()))
    return rows


def _latency_row_from_pass(label: str, results: PassResults) -> LatencyRow:
    """Map one pass ``PassResults`` to a latency table row."""
    latency = results.request_latency_ms
    return LatencyRow(
        label=label,
        request_p50_ms=latency.p50,
        request_p90_ms=latency.p90,
        request_p99_ms=latency.p99,
        per_post_p50_ms=results.per_post_latency_ms_p50,
        wall_time_seconds=_format_seconds(results.wall_time_seconds),
    )


def _latency_row_from_pr20(results: Pr20Results) -> LatencyRow:
    """Map PR 20 latency metrics to a latency table row."""
    return LatencyRow(
        label=PR20_ROW_LABEL,
        request_p50_ms=results.p50,
        request_p90_ms=results.p90,
        request_p99_ms=results.p99,
        per_post_p50_ms=results.p50,
        wall_time_seconds="not recorded",
    )


def _build_cost_rows(pass_results: dict[int, PassResults]) -> list[CostRow]:
    """Build cost table rows for all batch sizes and PR 20."""
    rows = [
        _cost_row_from_pass(str(batch_size), pass_results[batch_size])
        for batch_size in BATCH_SIZES
    ]
    rows.append(_cost_row_from_pr20(_load_pr20_results()))
    return rows


def _cost_row_from_pass(label: str, results: PassResults) -> CostRow:
    """Map one pass ``PassResults`` to a cost table row."""
    return CostRow(
        label=label,
        requests=results.n_requests,
        input_tokens=results.input_tokens,
        output_tokens=results.output_tokens,
        estimated_usd=results.estimated_cost_usd,
        usd_per_1000_posts=_usd_per_1000_posts(results.estimated_cost_usd),
    )


def _cost_row_from_pr20(results: Pr20Results) -> CostRow:
    """Map PR 20 token totals to a cost table row."""
    estimated_usd = estimate_jev_cost_usd(
        results.total_input_tokens,
        results.total_output_tokens,
    )
    return CostRow(
        label=PR20_ROW_LABEL,
        requests=results.n_scored,
        input_tokens=results.total_input_tokens,
        output_tokens=results.total_output_tokens,
        estimated_usd=estimated_usd,
        usd_per_1000_posts=_usd_per_1000_posts(estimated_usd),
    )


def _usd_per_1000_posts(estimated_usd: float) -> float:
    """Scale one pass estimated USD to a per-1,000-post cost."""
    return estimated_usd * 1000 / POSTS_PER_RUN


def _write_comparison_plot(pass_results: dict[int, PassResults]) -> Path:
    """Write the F1 and per-post latency comparison plot."""
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    plot_path = COMPARISON_DIR / PLOT_FILENAME
    batch_sizes = list(BATCH_SIZES)
    f1_values = [pass_results[size].f1 for size in BATCH_SIZES]
    latency_values = [pass_results[size].per_post_latency_ms_p50 for size in BATCH_SIZES]
    figure, axis = plt.subplots()
    axis.plot(batch_sizes, f1_values, color="tab:blue", marker="o", label="F1")
    axis.set_xlabel("batch size")
    axis.set_ylabel("F1", color="tab:blue")
    axis.tick_params(axis="y", labelcolor="tab:blue")
    latency_axis = axis.twinx()
    latency_axis.plot(
        batch_sizes,
        latency_values,
        color="tab:orange",
        marker="s",
        label="per-post p50 latency (ms)",
    )
    latency_axis.set_ylabel("per-post p50 latency (ms)", color="tab:orange")
    latency_axis.tick_params(axis="y", labelcolor="tab:orange")
    figure.savefig(plot_path)
    plt.close(figure)
    return plot_path


def _render_results_markdown(
    quality_rows: list[QualityRow],
    latency_rows: list[LatencyRow],
    cost_rows: list[CostRow],
    drift_rows: list[DriftRow],
    plot_path: Path,
) -> str:
    """Render the root ``RESULTS.md`` markdown document."""
    lines = [
        "# Results",
        "",
        f"Model versions: {TODAY_MODEL_VERSION} (this run), {PR20_MODEL_NAME} (PR 20).",
        f"Price source: {PRICE_SOURCE}.",
        "",
        f"Plot: `{plot_path.relative_to(EXPERIMENT_ROOT).as_posix()}`",
        "",
        *_batch_result_links(),
        "",
        "## Quality",
        "",
        *_quality_table_lines(quality_rows),
        "",
        "## Latency",
        "",
        *_latency_table_lines(latency_rows),
        "",
        "## Cost",
        "",
        *_cost_table_lines(cost_rows),
        "",
        "## Drift from batch size 1",
        "",
        *_drift_table_lines(drift_rows),
        "",
        "## Notes",
        "",
        f"- {NOTE_BASELINE}",
        f"- {NOTE_RATE_LIMIT}",
        f"- {NOTE_PR20_WALL_TIME}",
        f"- {NOTE_DRIFT}",
        "",
    ]
    return "\n".join(lines)


def _batch_result_links() -> list[str]:
    """Return markdown links to per-batch RESULTS files."""
    lines = ["Per-batch RESULTS:"]
    for batch_size in BATCH_SIZES:
        path = f"outputs/batch_{batch_size}/RESULTS.md"
        lines.append(f"- batch size {batch_size}: `{path}`")
    return lines


def _quality_table_lines(rows: list[QualityRow]) -> list[str]:
    """Build markdown lines for the quality comparison table."""
    header = (
        "| batch size | f1 | accuracy | precision | recall | scored | deadletter |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"
    body = [
        _format_quality_row(row)
        for row in rows
    ]
    return [header, separator, *body]


def _format_quality_row(row: QualityRow) -> str:
    """Format one quality table row."""
    return (
        f"| {row.label} | {_format_metric(row.f1)} | {_format_metric(row.accuracy)} | "
        f"{_format_metric(row.precision)} | {_format_metric(row.recall)} | "
        f"{row.scored} | {row.deadletter} |"
    )


def _latency_table_lines(rows: list[LatencyRow]) -> list[str]:
    """Build markdown lines for the latency comparison table."""
    header = (
        "| batch size | request p50 (ms) | request p90 (ms) | request p99 (ms) | "
        "per-post p50 (ms) | wall time (s) |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: |"
    body = [_format_latency_row(row) for row in rows]
    return [header, separator, *body]


def _format_latency_row(row: LatencyRow) -> str:
    """Format one latency table row."""
    return (
        f"| {row.label} | {_format_ms(row.request_p50_ms)} | "
        f"{_format_ms(row.request_p90_ms)} | {_format_ms(row.request_p99_ms)} | "
        f"{_format_ms(row.per_post_p50_ms)} | {row.wall_time_seconds} |"
    )


def _cost_table_lines(rows: list[CostRow]) -> list[str]:
    """Build markdown lines for the cost comparison table."""
    header = (
        "| batch size | requests | input tokens | output tokens | "
        "estimated USD | USD per 1,000 posts |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: |"
    body = [_format_cost_row(row) for row in rows]
    return [header, separator, *body]


def _format_cost_row(row: CostRow) -> str:
    """Format one cost table row."""
    return (
        f"| {row.label} | {row.requests} | {row.input_tokens} | {row.output_tokens} | "
        f"{_format_usd(row.estimated_usd)} | {_format_usd(row.usd_per_1000_posts)} |"
    )


def _drift_table_lines(rows: list[DriftRow]) -> list[str]:
    """Build markdown lines for the drift comparison table."""
    header = "| batch size | label agreement | mean abs prob diff |"
    separator = "| --- | ---: | ---: |"
    body = [_format_drift_row(row) for row in rows]
    return [header, separator, *body]


def _format_drift_row(row: DriftRow) -> str:
    """Format one drift table row."""
    return (
        f"| {row.label} | {_format_metric(row.agreement)} | "
        f"{_format_metric(row.mean_abs_prob_diff)} |"
    )


def _format_metric(value: float) -> str:
    """Format a metric value with fixed decimal places."""
    return f"{value:.{METRIC_DECIMALS}f}"


def _format_ms(value: float) -> str:
    """Format a millisecond value with fixed decimal places."""
    return f"{value:.{MS_DECIMALS}f}"


def _format_seconds(value: float) -> str:
    """Format a seconds value with fixed decimal places."""
    return f"{value:.{SECONDS_DECIMALS}f}"


def _format_usd(value: float) -> str:
    """Format a USD value with fixed decimal places."""
    return f"{value:.{USD_DECIMALS}f}"


if __name__ == "__main__":
    main()
