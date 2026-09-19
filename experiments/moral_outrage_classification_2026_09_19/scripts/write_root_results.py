"""Fill the root RESULTS file from per-model results.json files.

Run from the experiment folder:

    uv run python scripts/write_root_results.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from shared.metrics import paired_difference_summary
from shared.pricing import smoke_model_order

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
COMPARISON_DIR = OUTPUTS_DIR / "comparison"
RESULTS_PATH = EXPERIMENT_ROOT / "RESULTS.md"
PERSPECTIVE_EMPTY_SAMPLE_IDS = (
    "1990",
    "6429",
    "19057",
    "19803",
    "19853",
    "19977",
    "22320",
)


def write_root_results(
    outputs_dir: Path, results_path: Path, comparison_dir: Path
) -> dict[str, object]:
    """Write root RESULTS.md, histograms, and difference_summary.json."""
    payloads = _load_payloads(outputs_dir)
    missing = [name for name in smoke_model_order() if name not in payloads]
    if missing:
        raise SystemExit(f"Missing results.json for: {', '.join(missing)}")
    jev_labels = _load_labels(outputs_dir / "jev" / "labels.parquet")
    perspective_labels = _load_labels(
        outputs_dir / "perspective_api" / "labels.parquet"
    )
    paired, n_dropped = pair_probabilities(jev_labels, perspective_labels)
    summary = _difference_summary(paired, n_dropped)
    comparison_dir.mkdir(parents=True, exist_ok=True)
    _write_histograms(jev_labels, perspective_labels, paired, comparison_dir)
    (comparison_dir / "difference_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    results_path.write_text(
        render_root_results(payloads, summary), encoding="utf-8"
    )
    return summary


def pair_probabilities(
    jev_labels: pd.DataFrame, perspective_labels: pd.DataFrame
) -> tuple[pd.DataFrame, int]:
    """Inner-join probabilities on source_row_id. Count dropped ids."""
    if jev_labels.empty or perspective_labels.empty:
        all_ids = set()
        if not jev_labels.empty:
            all_ids.update(jev_labels["source_row_id"].astype(str))
        if not perspective_labels.empty:
            all_ids.update(perspective_labels["source_row_id"].astype(str))
        return (
            pd.DataFrame(columns=["source_row_id", "jev", "perspective"]),
            len(all_ids),
        )
    all_ids = set(jev_labels["source_row_id"].astype(str)).union(
        set(perspective_labels["source_row_id"].astype(str))
    )
    jev = jev_labels.dropna(subset=["probability"])[
        ["source_row_id", "probability"]
    ].rename(columns={"probability": "jev"})
    perspective = perspective_labels.dropna(subset=["probability"])[
        ["source_row_id", "probability"]
    ].rename(columns={"probability": "perspective"})
    merged = jev.merge(perspective, on="source_row_id", how="inner")
    n_dropped = len(all_ids) - len(merged)
    return merged, n_dropped


def render_root_results(
    payloads: dict[str, dict[str, object]], summary: dict[str, object]
) -> str:
    """Render the locked root RESULTS sections."""
    order = smoke_model_order()
    quality = _markdown_table(
        order,
        payloads,
        ("f1", "accuracy", "precision", "recall"),
        "Quality",
    )
    latency = _markdown_table(order, payloads, ("p50", "p90", "p99"), "Latency")
    cost = _cost_table(order, payloads)
    deadletters = "\n".join(
        f"- {name}: {payloads.get(name, {}).get('n_deadletter', 'missing')}"
        for name in order
    )
    perspective_n = payloads.get("Perspective API", {}).get("n_scored", 993)
    missing_ids = ", ".join(f"`{row_id}`" for row_id in PERSPECTIVE_EMPTY_SAMPLE_IDS)
    return (
        "# Results\n\n"
        "Scores are on the 1,000-row stratified sample (560 gold 0, 440 gold 1), "
        "seed `20260919`.\n\n"
        f"Perspective classification metrics used {perspective_n} rows. "
        "These sample `source_row_id` values have an empty stored `pred_label` "
        f"and were dropped: {missing_ids}.\n\n"
        f"{quality}\n\n"
        f"{latency}\n\n"
        f"{cost}\n\n"
        "## Calibration\n\n"
        "Bar histograms: `outputs/comparison/jev_hist.png` and "
        "`outputs/comparison/perspective_hist.png`. Difference histogram: "
        "`outputs/comparison/difference_hist.png`.\n\n"
        f"- paired rows: {summary['n_paired']}\n"
        f"- dropped for a missing probability: {summary['n_dropped']}\n"
        f"- mean: {summary['mean']}\n"
        f"- median: {summary['median']}\n"
        f"- std: {summary['std']}\n"
        f"- iqr: {summary['iqr']}\n\n"
        "## Deadletter counts\n\n"
        f"{deadletters}\n\n"
        "Region, secrets, and model ids: see SETUP.md.\n"
    )


def _load_payloads(outputs_dir: Path) -> dict[str, dict[str, object]]:
    payloads: dict[str, dict[str, object]] = {}
    for name, relative in (
        ("Jev", Path("jev") / "results.json"),
        ("Perspective API", Path("perspective_api") / "results.json"),
        (
            "Bedrock:us.openai.gpt-5.6-luna",
            Path("bedrock") / "us.openai.gpt-5.6-luna" / "results.json",
        ),
        (
            "Bedrock:us.openai.gpt-5.6-terra",
            Path("bedrock") / "us.openai.gpt-5.6-terra" / "results.json",
        ),
        (
            "Bedrock:us.anthropic.claude-sonnet-5",
            Path("bedrock") / "us.anthropic.claude-sonnet-5" / "results.json",
        ),
        (
            "Bedrock:qwen.qwen3-32b-v1:0",
            Path("bedrock") / "qwen.qwen3-32b-v1:0" / "results.json",
        ),
        (
            "Bedrock:deepseek.v3-v1:0",
            Path("bedrock") / "deepseek.v3-v1:0" / "results.json",
        ),
    ):
        path = outputs_dir / relative
        if path.is_file():
            payloads[name] = json.loads(path.read_text(encoding="utf-8"))
    return payloads


def _load_labels(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _difference_summary(
    paired: pd.DataFrame, n_dropped: int
) -> dict[str, object]:
    if paired.empty:
        stats = {"mean": 0.0, "median": 0.0, "std": 0.0, "iqr": 0.0}
    else:
        stats = paired_difference_summary(
            list(paired["jev"]), list(paired["perspective"])
        )
    return {**stats, "n_paired": int(len(paired)), "n_dropped": int(n_dropped)}


def _write_histograms(
    jev_labels: pd.DataFrame,
    perspective_labels: pd.DataFrame,
    paired: pd.DataFrame,
    comparison_dir: Path,
) -> None:
    _save_hist(
        list(jev_labels["probability"].dropna()) if not jev_labels.empty else [],
        comparison_dir / "jev_hist.png",
        "Jev probability",
    )
    _save_hist(
        list(perspective_labels["probability"].dropna())
        if not perspective_labels.empty
        else [],
        comparison_dir / "perspective_hist.png",
        "Perspective probability",
    )
    diffs = (
        list(paired["jev"] - paired["perspective"]) if not paired.empty else []
    )
    _save_hist(diffs, comparison_dir / "difference_hist.png", "Jev minus Perspective")


def _save_hist(values: list[float], path: Path, title: str) -> None:
    figure, axis = plt.subplots()
    if values:
        axis.hist(values, bins=10)
    axis.set_title(title)
    figure.savefig(path)
    plt.close(figure)


def _markdown_table(
    order: tuple[str, ...],
    payloads: dict[str, dict[str, object]],
    columns: tuple[str, ...],
    heading: str,
) -> str:
    header = "| model name | " + " | ".join(columns) + " |"
    sep = "| --- | " + " | ".join("---:" for _ in columns) + " |"
    lines = [f"## {heading}\n", header, sep]
    for name in order:
        payload = payloads.get(name, {})
        cells = [name] + [str(payload.get(column, "")) for column in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _cost_table(
    order: tuple[str, ...], payloads: dict[str, dict[str, object]]
) -> str:
    lines = [
        "## Cost\n",
        "| model name | total tokens | estimated cost USD |",
        "| --- | ---: | ---: |",
    ]
    for name in order:
        payload = payloads.get(name, {})
        tokens = int(payload.get("total_input_tokens", 0) or 0) + int(
            payload.get("total_output_tokens", 0) or 0
        )
        cost = "unknown" if name == "Jev" else payload.get("estimated_cost_usd", "")
        if name == "Perspective API":
            cost = 0
        lines.append(f"| {name} | {tokens} | {cost} |")
    return "\n".join(lines)


def main() -> None:
    write_root_results(OUTPUTS_DIR, RESULTS_PATH, COMPARISON_DIR)


if __name__ == "__main__":
    main()
