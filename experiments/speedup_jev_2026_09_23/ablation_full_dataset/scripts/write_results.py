"""Write ablation RESULTS and comparison plot after all full passes complete.

Run from the experiment folder:

    uv run python ablation_full_dataset/scripts/write_results.py
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

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_ROOT = EXPERIMENT_ROOT / "scripts"
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from run_batch_size import PassResults  # noqa: E402
from shared.data import load_sample  # noqa: E402
from shared.full_dataset import ABLATION_BATCH_SIZES, SHUFFLE_SEED  # noqa: E402
from shared.metrics import (  # noqa: E402
    agreement_rate,
    classification_report,
    mean_absolute_difference,
)
from shared.pricing import PRICE_PAGE_DATE, PRICE_PAGE_URL  # noqa: E402
from shared.rate_limiter import MAX_REQUEST_STARTS_PER_MINUTE  # noqa: E402

MAIN_REFERENCE_F1_BATCH1 = 0.752
FULL_DATA_BASELINE_BATCH_SIZE = 10
PROJECTION_REQUESTS_PER_MIN = 1000
PROJECTION_TYPESAFE_REQUESTS_PER_MIN = 1200
PROJECTION_POSTS_20M = 20_000_000
BATCH_SIZE_10_CAP_FLOOR_SECONDS = 120.0
CAP_BOUND_YES = "yes"
CAP_BOUND_NO = "no"
MODEL_VERSION = "jev-1.13.0"
SAME_POSTS_BATCH_SIZES = (10, 20, 40)
METRIC_DECIMALS = 3
MS_DECIMALS = 1
SECONDS_DECIMALS = 1
HOURS_DECIMALS = 1
USD_SMALL_DECIMALS = 6
USD_LARGE_DECIMALS = 2
THROUGHPUT_DECIMALS = 1
ROW_ID_COLUMN = "source_row_id"
BINARY_LABEL_COLUMN = "binary_label"
PROBABILITY_COLUMN = "probability"
GOLD_LABEL_COLUMN = "gold_label"
ABLATION_ROOT = EXPERIMENT_ROOT / "ablation_full_dataset"
OUTPUTS_DIR = ABLATION_ROOT / "outputs"
COMPARISON_DIR = OUTPUTS_DIR / "comparison"
RESULTS_PATH = ABLATION_ROOT / "RESULTS.md"
PLOT_FILENAME = "f1_and_latency_by_batch_size.png"
PRICE_SOURCE = f"{PRICE_PAGE_URL} ({PRICE_PAGE_DATE})"
REFERENCE_F1_LABEL = (
    "share of main-run batch size 1 F1 (0.752 on 1,000-post sample)"
)
RATE_CAP_REQUEST_FLOOR = 1000
RATE_CAP_SECONDS_PER_EXTRA_THOUSAND = 60.0
MEASURED_THROUGHPUT_FOOTNOTE = (
    "Measured posts per minute for passes that were not cap bound reflects a "
    "burst below the cap and is not a sustainable rate."
)


class QualityRow(BaseModel):
    """One quality table row."""

    batch_size: int
    f1: float
    accuracy: float
    precision: float
    recall: float
    scored: int
    deadletter: int
    share_of_reference_f1: float


class LatencyRow(BaseModel):
    """One latency table row."""

    batch_size: int
    request_p50_ms: float
    request_p90_ms: float
    request_p99_ms: float
    per_post_p50_ms: float
    wall_time_seconds: float
    measured_posts_per_min_burst: float
    projected_posts_per_min: float
    cap_bound: bool


class CostRow(BaseModel):
    """One cost table row."""

    batch_size: int
    requests: int
    input_tokens: int
    output_tokens: int
    estimated_usd: float
    usd_per_1000_posts: float
    projected_hours_20m_cap: float
    projected_hours_20m_typesafe: float
    projected_usd_20m: float


class DriftRow(BaseModel):
    """One drift table row."""

    batch_size: int
    agreement: float
    mean_abs_prob_diff: float


class SamePostsRow(BaseModel):
    """One same-posts comparison row."""

    batch_size: int
    ablation_f1: float
    main_f1: float
    label_agreement: float
    share_of_reference_f1: float


def main() -> None:
    """Build ablation comparison tables, plot, and RESULTS markdown."""
    pass_results = _load_all_pass_results()
    sample_ids = _sample_row_ids()
    baseline_labels = _load_ablation_labels(FULL_DATA_BASELINE_BATCH_SIZE)
    quality_rows = _build_quality_rows(pass_results)
    latency_rows = _build_latency_rows(pass_results)
    cost_rows = _build_cost_rows(pass_results)
    drift_rows = _build_drift_rows(baseline_labels)
    same_posts_rows = _build_same_posts_rows(sample_ids)
    plot_path = _write_comparison_plot(pass_results)
    notes = _build_notes(pass_results)
    markdown = _render_results_markdown(
        quality_rows,
        latency_rows,
        cost_rows,
        drift_rows,
        same_posts_rows,
        plot_path,
        notes,
    )
    RESULTS_PATH.write_text(markdown, encoding="utf-8")


def _load_all_pass_results() -> dict[int, PassResults]:
    """Load ``results.json`` for every ablation batch size."""
    results: dict[int, PassResults] = {}
    for batch_size in ABLATION_BATCH_SIZES:
        results[batch_size] = _load_pass_results(batch_size)
    return results


def _load_pass_results(batch_size: int) -> PassResults:
    """Load one ablation pass ``results.json`` by batch size."""
    path = OUTPUTS_DIR / f"batch_{batch_size}" / "results.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PassResults.model_validate(payload)


def _sample_row_ids() -> set[str]:
    """Return the 1,000 main-sample ``source_row_id`` values as strings."""
    sample = load_sample()
    return set(sample[ROW_ID_COLUMN].astype(str).tolist())


def _load_ablation_labels(batch_size: int) -> pd.DataFrame:
    """Load ablation label columns for one batch-size pass."""
    path = OUTPUTS_DIR / f"batch_{batch_size}" / "labels.parquet"
    frame = pd.read_parquet(path)
    return frame[[ROW_ID_COLUMN, GOLD_LABEL_COLUMN, BINARY_LABEL_COLUMN, PROBABILITY_COLUMN]]


def _load_main_labels(batch_size: int) -> pd.DataFrame:
    """Load main-run label columns for one batch-size pass."""
    path = EXPERIMENT_ROOT / "outputs" / f"batch_{batch_size}" / "labels.parquet"
    frame = pd.read_parquet(path)
    return frame[[ROW_ID_COLUMN, GOLD_LABEL_COLUMN, BINARY_LABEL_COLUMN, PROBABILITY_COLUMN]]


def _filter_labels(frame: pd.DataFrame, row_ids: set[str]) -> pd.DataFrame:
    """Keep rows whose ``source_row_id`` is in ``row_ids``."""
    mask = frame[ROW_ID_COLUMN].astype(str).isin(row_ids)
    return frame.loc[mask].copy()


def _f1_from_labels(frame: pd.DataFrame) -> float:
    """Compute F1 from a labels frame with gold and binary columns."""
    gold = frame[GOLD_LABEL_COLUMN].astype(int).tolist()
    pred = frame[BINARY_LABEL_COLUMN].astype(int).tolist()
    return classification_report(gold, pred)["f1"]


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


def _build_quality_rows(pass_results: dict[int, PassResults]) -> list[QualityRow]:
    """Build quality metrics rows for all ablation batch sizes."""
    rows: list[QualityRow] = []
    for batch_size in ABLATION_BATCH_SIZES:
        results = pass_results[batch_size]
        rows.append(
            QualityRow(
                batch_size=batch_size,
                f1=results.f1,
                accuracy=results.accuracy,
                precision=results.precision,
                recall=results.recall,
                scored=results.n_scored,
                deadletter=results.n_deadletter,
                share_of_reference_f1=results.f1 / MAIN_REFERENCE_F1_BATCH1,
            )
        )
    return rows


def _measured_posts_per_min_burst(results: PassResults) -> float:
    """Return measured posts per minute including the first-minute burst."""
    return results.n_scored / results.wall_time_seconds * 60.0


def _projected_posts_per_min(batch_size: int) -> float:
    """Return cap-based projected posts per minute."""
    return float(PROJECTION_REQUESTS_PER_MIN * batch_size)


def _build_latency_rows(pass_results: dict[int, PassResults]) -> list[LatencyRow]:
    """Build latency table rows for all ablation batch sizes."""
    rows: list[LatencyRow] = []
    for batch_size in ABLATION_BATCH_SIZES:
        results = pass_results[batch_size]
        latency = results.request_latency_ms
        rows.append(
            LatencyRow(
                batch_size=batch_size,
                request_p50_ms=latency.p50,
                request_p90_ms=latency.p90,
                request_p99_ms=latency.p99,
                per_post_p50_ms=results.per_post_latency_ms_p50,
                wall_time_seconds=results.wall_time_seconds,
                measured_posts_per_min_burst=_measured_posts_per_min_burst(results),
                projected_posts_per_min=_projected_posts_per_min(batch_size),
                cap_bound=_rate_cap_bound(
                    results.n_requests,
                    results.wall_time_seconds,
                ),
            )
        )
    return rows


def _usd_per_1000_posts(estimated_usd: float, n_scored: int) -> float:
    """Scale one pass estimated USD to a per-1,000-post cost."""
    return estimated_usd * 1000.0 / n_scored


def _projected_hours_20m_cap(batch_size: int) -> float:
    """Return projected wall hours for 20M posts at the request cap."""
    requests_20m = PROJECTION_POSTS_20M / batch_size
    return requests_20m / PROJECTION_REQUESTS_PER_MIN / 60.0


def _projected_hours_20m_typesafe(batch_size: int) -> float:
    """Return projected wall hours for 20M posts at the TypeSafe limit."""
    requests_20m = PROJECTION_POSTS_20M / batch_size
    return requests_20m / PROJECTION_TYPESAFE_REQUESTS_PER_MIN / 60.0


def _projected_usd_20m(estimated_usd: float, n_scored: int) -> float:
    """Return projected USD for 20M posts from measured per-post cost."""
    return estimated_usd / n_scored * PROJECTION_POSTS_20M


def _build_cost_rows(pass_results: dict[int, PassResults]) -> list[CostRow]:
    """Build cost table rows for all ablation batch sizes."""
    rows: list[CostRow] = []
    for batch_size in ABLATION_BATCH_SIZES:
        results = pass_results[batch_size]
        rows.append(
            CostRow(
                batch_size=batch_size,
                requests=results.n_requests,
                input_tokens=results.input_tokens,
                output_tokens=results.output_tokens,
                estimated_usd=results.estimated_cost_usd,
                usd_per_1000_posts=_usd_per_1000_posts(
                    results.estimated_cost_usd,
                    results.n_scored,
                ),
                projected_hours_20m_cap=_projected_hours_20m_cap(batch_size),
                projected_hours_20m_typesafe=_projected_hours_20m_typesafe(batch_size),
                projected_usd_20m=_projected_usd_20m(
                    results.estimated_cost_usd,
                    results.n_scored,
                ),
            )
        )
    return rows


def _build_drift_rows(baseline_labels: pd.DataFrame) -> list[DriftRow]:
    """Build drift table rows against full-data batch size 10."""
    rows: list[DriftRow] = []
    for batch_size in ABLATION_BATCH_SIZES:
        labels = _load_ablation_labels(batch_size)
        agreement, mad = _compute_drift(baseline_labels, labels)
        rows.append(
            DriftRow(
                batch_size=batch_size,
                agreement=agreement,
                mean_abs_prob_diff=mad,
            )
        )
    return rows


def _label_agreement_on_ids(
    left: pd.DataFrame,
    right: pd.DataFrame,
    row_ids: set[str],
) -> float:
    """Return binary label agreement on overlapping sample ids."""
    left_filtered = _filter_labels(left, row_ids)
    right_filtered = _filter_labels(right, row_ids)
    merged = left_filtered.merge(
        right_filtered,
        on=ROW_ID_COLUMN,
        suffixes=("_left", "_right"),
    )
    left_binary = merged[f"{BINARY_LABEL_COLUMN}_left"].astype(int).tolist()
    right_binary = merged[f"{BINARY_LABEL_COLUMN}_right"].astype(int).tolist()
    return agreement_rate(left_binary, right_binary)


def _build_same_posts_rows(sample_ids: set[str]) -> list[SamePostsRow]:
    """Build same-posts comparison rows for selected batch sizes."""
    rows: list[SamePostsRow] = []
    for batch_size in SAME_POSTS_BATCH_SIZES:
        ablation_labels = _load_ablation_labels(batch_size)
        main_labels = _load_main_labels(batch_size)
        ablation_sample = _filter_labels(ablation_labels, sample_ids)
        main_sample = _filter_labels(main_labels, sample_ids)
        ablation_f1 = _f1_from_labels(ablation_sample)
        main_f1 = _f1_from_labels(main_sample)
        agreement = _label_agreement_on_ids(ablation_labels, main_labels, sample_ids)
        rows.append(
            SamePostsRow(
                batch_size=batch_size,
                ablation_f1=ablation_f1,
                main_f1=main_f1,
                label_agreement=agreement,
                share_of_reference_f1=ablation_f1 / MAIN_REFERENCE_F1_BATCH1,
            )
        )
    return rows


def _rate_cap_bound(n_requests: int, wall_time_seconds: float) -> bool:
    """Return whether the 1,000 request/min cap likely bound this pass."""
    if n_requests <= RATE_CAP_REQUEST_FLOOR:
        return False
    floor_seconds = RATE_CAP_SECONDS_PER_EXTRA_THOUSAND * (
        n_requests / RATE_CAP_REQUEST_FLOOR - 1.0
    )
    return wall_time_seconds >= floor_seconds


def _build_notes(pass_results: dict[int, PassResults]) -> list[str]:
    """Build factual notes from constants and pass metrics."""
    batch_10 = pass_results[FULL_DATA_BASELINE_BATCH_SIZE]
    return [
        "This is a separate ablation from the main 1,000-post experiment.",
        "There is no batch size 1 pass on the full 26,000-post data.",
        f"Posts were shuffled once with seed {SHUFFLE_SEED} before batching.",
        f"The model is {MODEL_VERSION}.",
        (
            "Reference F1 0.752 is from the main run at batch size 1 on the "
            "1,000-post sample, not the full data."
        ),
        (
            "The request start cap counts starts in a rolling 60 s window, "
            "so each pass starts with a burst of up to 1,000 requests."
        ),
        "Passes with fewer than 1,000 requests never waited on the cap.",
        (
            "Over 20M posts the burst is negligible, so the projection uses "
            "the cap rate."
        ),
        (
            f"Batch size 10 wall time of "
            f"{_format_seconds(batch_10.wall_time_seconds)} s is consistent with "
            "the cap floor of two full 60 s windows plus the remainder "
            f"(about {_format_seconds(BATCH_SIZE_10_CAP_FLOOR_SECONDS)} s minimum "
            f"for {batch_10.n_requests} starts)."
        ),
    ]


def _write_comparison_plot(pass_results: dict[int, PassResults]) -> Path:
    """Write the F1 and per-post latency comparison plot."""
    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    plot_path = COMPARISON_DIR / PLOT_FILENAME
    batch_sizes = list(ABLATION_BATCH_SIZES)
    f1_values = [pass_results[size].f1 for size in ABLATION_BATCH_SIZES]
    latency_values = [
        pass_results[size].per_post_latency_ms_p50 for size in ABLATION_BATCH_SIZES
    ]
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
    same_posts_rows: list[SamePostsRow],
    plot_path: Path,
    notes: list[str],
) -> str:
    """Render the ablation ``RESULTS.md`` markdown document."""
    lines = [
        "# Full 26k dataset ablation results",
        "",
        f"Model: {MODEL_VERSION}. Price source: {PRICE_SOURCE}.",
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
        MEASURED_THROUGHPUT_FOOTNOTE,
        "",
        "## Cost",
        "",
        *_cost_table_lines(cost_rows),
        "",
        f"## Drift from batch size {FULL_DATA_BASELINE_BATCH_SIZE} on full data",
        "",
        *_drift_table_lines(drift_rows),
        "",
        "## Same-posts comparison (1,000 main-sample ids)",
        "",
        *_same_posts_table_lines(same_posts_rows),
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in notes],
        "",
    ]
    return "\n".join(lines)


def _batch_result_links() -> list[str]:
    """Return markdown links to per-batch RESULTS files."""
    lines = ["Per-batch RESULTS:"]
    for batch_size in ABLATION_BATCH_SIZES:
        path = f"ablation_full_dataset/outputs/batch_{batch_size}/RESULTS.md"
        lines.append(f"- batch size {batch_size}: `{path}`")
    return lines


def _quality_table_lines(rows: list[QualityRow]) -> list[str]:
    """Build markdown lines for the quality comparison table."""
    header = (
        "| batch size | f1 | accuracy | precision | recall | scored | deadletter | "
        f"{REFERENCE_F1_LABEL} |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    body = [_format_quality_row(row) for row in rows]
    return [header, separator, *body]


def _format_quality_row(row: QualityRow) -> str:
    """Format one quality table row."""
    return (
        f"| {row.batch_size} | {_format_metric(row.f1)} | "
        f"{_format_metric(row.accuracy)} | {_format_metric(row.precision)} | "
        f"{_format_metric(row.recall)} | {row.scored} | {row.deadletter} | "
        f"{_format_metric(row.share_of_reference_f1)} |"
    )


def _latency_table_lines(rows: list[LatencyRow]) -> list[str]:
    """Build markdown lines for the latency comparison table."""
    header = (
        "| batch size | request p50 (ms) | request p90 (ms) | request p99 (ms) | "
        "per-post p50 (ms) | wall time (s) | measured posts per minute "
        "(includes first-minute burst) | projected posts/min | cap bound |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    body = [_format_latency_row(row) for row in rows]
    return [header, separator, *body]


def _format_latency_row(row: LatencyRow) -> str:
    """Format one latency table row."""
    return (
        f"| {row.batch_size} | {_format_ms(row.request_p50_ms)} | "
        f"{_format_ms(row.request_p90_ms)} | {_format_ms(row.request_p99_ms)} | "
        f"{_format_ms(row.per_post_p50_ms)} | "
        f"{_format_seconds(row.wall_time_seconds)} | "
        f"{_format_throughput(row.measured_posts_per_min_burst)} | "
        f"{_format_throughput(row.projected_posts_per_min)} | "
        f"{_format_cap_bound(row.cap_bound)} |"
    )


def _format_cap_bound(cap_bound: bool) -> str:
    """Format cap-bound flag as yes or no."""
    if cap_bound:
        return CAP_BOUND_YES
    return CAP_BOUND_NO


def _cost_table_lines(rows: list[CostRow]) -> list[str]:
    """Build markdown lines for the cost comparison table."""
    header = (
        "| batch size | requests | input tokens | output tokens | estimated USD | "
        "USD per 1,000 posts | 20M hours (1,000 req/min cap) | "
        "20M hours (1,200 req/min limit) | 20M USD |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    body = [_format_cost_row(row) for row in rows]
    return [header, separator, *body]


def _format_cost_row(row: CostRow) -> str:
    """Format one cost table row."""
    return (
        f"| {row.batch_size} | {row.requests} | {row.input_tokens} | "
        f"{row.output_tokens} | {_format_usd(row.estimated_usd)} | "
        f"{_format_usd(row.usd_per_1000_posts)} | "
        f"{_format_hours(row.projected_hours_20m_cap)} | "
        f"{_format_hours(row.projected_hours_20m_typesafe)} | "
        f"{_format_usd(row.projected_usd_20m)} |"
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
        f"| {row.batch_size} | {_format_metric(row.agreement)} | "
        f"{_format_metric(row.mean_abs_prob_diff)} |"
    )


def _same_posts_table_lines(rows: list[SamePostsRow]) -> list[str]:
    """Build markdown lines for the same-posts comparison table."""
    header = (
        "| batch size | ablation F1 on sample | main-run F1 on sample | "
        "label agreement | share of reference F1 (0.752) |"
    )
    separator = "| --- | ---: | ---: | ---: | ---: |"
    body = [_format_same_posts_row(row) for row in rows]
    return [header, separator, *body]


def _format_same_posts_row(row: SamePostsRow) -> str:
    """Format one same-posts table row."""
    return (
        f"| {row.batch_size} | {_format_metric(row.ablation_f1)} | "
        f"{_format_metric(row.main_f1)} | {_format_metric(row.label_agreement)} | "
        f"{_format_metric(row.share_of_reference_f1)} |"
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


def _format_hours(value: float) -> str:
    """Format an hours value with fixed decimal places."""
    return f"{value:.{HOURS_DECIMALS}f}"


def _format_throughput(value: float) -> str:
    """Format a posts-per-minute value with fixed decimal places."""
    return f"{value:.{THROUGHPUT_DECIMALS}f}"


def _format_usd(value: float) -> str:
    """Format a USD value with small or large decimal places."""
    if value < 1.0:
        return f"{value:.{USD_SMALL_DECIMALS}f}"
    return f"{value:.{USD_LARGE_DECIMALS}f}"


if __name__ == "__main__":
    main()
