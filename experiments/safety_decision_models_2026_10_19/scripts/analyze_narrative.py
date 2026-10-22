"""Narrative figures and supplementary metrics from cached predictions only.

Does not invoke scorers or paid APIs. Writes under outputs/figures/narrative_20261020/.
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from scorers.guardrails import band_blocks_at_strength  # noqa: E402
from shared.metrics import (  # noqa: E402
    binary_f1,
    ece_score,
    false_positive_rate,
    miss_rate,
)
from shared.records import ExampleRecord, PredictionRecord  # noqa: E402
from shared.thresholds import FIXED_THRESHOLD, CascadeThresholds  # noqa: E402

# Reuse metric helpers without running run_metrics.main()
from scripts.run_metrics import (  # noqa: E402
    GUARDRAIL_ARM,
    MODEL_ARMS,
    RUN_ID,
    STACK_STRENGTH,
    _harmful_for_stack,
    _is_harm_row,
    _jailbreakbench_harm_benign,
    _sensitivity_band_lookup,
    _stack_policy_blocks,
    align_predictions,
    harm_score,
    load_predictions,
    model_blocks,
)

METRICS_PATH = EXPERIMENT_ROOT / "outputs" / "metrics" / f"{RUN_ID}.json"
RECORDS_DIR = EXPERIMENT_ROOT / "data" / "records"
OUT_DIR = EXPERIMENT_ROOT / "outputs" / "figures" / "narrative_20261020"
DPI = 160
BOOTSTRAP_N = 1000
BOOTSTRAP_SEED = 42

# Okabe–Ito colorblind-safe palette
PALETTE = {
    "jev": "#0072B2",
    "clef": "#E69F00",
    "clef-flash": "#009E73",
    "guardrails": "#CC79A7",
    "guardrail_crosswalk": "#000000",
    "post_hoc": "#D55E00",
    "union": "#56B4E9",
    "intersection": "#F0E442",
    "cascade": "#999999",
}


def _load_metrics() -> dict[str, Any]:
    if not METRICS_PATH.is_file():
        raise FileNotFoundError(f"missing metrics cache: {METRICS_PATH}")
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def _load_records(dataset: str) -> list[ExampleRecord]:
    path = RECORDS_DIR / f"{dataset}.parquet"
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_parquet(
        path,
        columns=[
            "example_id",
            "dataset",
            "split",
            "gold_labels",
            "harm_category",
            "is_benign_known",
            "metadata",
        ],
    )
    records: list[ExampleRecord] = []
    for row in frame.to_dict(orient="records"):
        if isinstance(row.get("gold_labels"), str):
            row["gold_labels"] = json.loads(row["gold_labels"])
        if isinstance(row.get("metadata"), str):
            row["metadata"] = json.loads(row["metadata"])
        row["text"] = ""
        records.append(ExampleRecord.model_validate(row))
    return records


def _load_all_predictions(
    datasets: list[str],
) -> dict[str, dict[str, list[PredictionRecord]]]:
    arms = (*MODEL_ARMS, GUARDRAIL_ARM)
    out: dict[str, dict[str, list[PredictionRecord]]] = {a: {} for a in arms}
    for arm in arms:
        for ds in datasets:
            preds = load_predictions(arm, ds)
            rows = _load_records(ds)
            out[arm][ds] = align_predictions(rows, preds)
    return out


def bootstrap_ci(
    indicators: list[float],
    *,
    n_resamples: int = BOOTSTRAP_N,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float]:
    if not indicators:
        return {"mean": math.nan, "ci_low": math.nan, "ci_high": math.nan}
    rng = random.Random(seed)
    n = len(indicators)
    stats: list[float] = []
    for _ in range(n_resamples):
        sample = [indicators[rng.randrange(n)] for _ in range(n)]
        stats.append(sum(sample) / n)
    stats.sort()
    low = stats[int(0.025 * len(stats))]
    high = stats[int(0.975 * len(stats))]
    return {
        "mean": sum(indicators) / n,
        "ci_low": low,
        "ci_high": high,
    }


def cohens_kappa(a: list[bool], b: list[bool]) -> float:
    if len(a) != len(b) or not a:
        return math.nan
    n = len(a)
    po = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    pa = sum(a) / n
    pb = sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def jaccard_blocks(a: list[bool], b: list[bool]) -> float:
    if len(a) != len(b) or not a:
        return math.nan
    inter = sum(1 for x, y in zip(a, b, strict=True) if x and y)
    union = sum(1 for x, y in zip(a, b, strict=True) if x or y)
    return inter / union if union else math.nan


def _crosswalk_band_lookup(
    rows: list[ExampleRecord], guard_preds: list[PredictionRecord]
) -> Callable[[str], str | None]:
    by_id = {p.example_id: (p.band or "NONE") for p in guard_preds}
    return lambda eid: by_id.get(eid)


def headline_miss_fpr_model(
    dataset: str,
    rows: list[ExampleRecord],
    preds: list[PredictionRecord],
    threshold: float,
) -> tuple[float, float]:
    blocks = model_blocks(dataset, rows, preds, threshold)
    if dataset == "jailbreakbench":
        harmful, benign = _jailbreakbench_harm_benign(rows)
        return (
            miss_rate(harmful, blocks) or math.nan,
            false_positive_rate(benign, blocks) or math.nan,
        )
    if dataset == "xstest":
        harmful = [bool(r.gold_labels.get("harmful")) for r in rows]  # type: ignore[union-attr]
        benign = [r.is_benign_known for r in rows]
        return (
            miss_rate(harmful, blocks) or math.nan,
            false_positive_rate(benign, blocks) or math.nan,
        )
    if dataset == "wildguardmix":
        harmful = [bool(r.gold_labels.get("prompt_harm")) for r in rows]  # type: ignore[union-attr]
        benign = [not h for h in harmful]
        return (
            miss_rate(harmful, blocks) or math.nan,
            false_positive_rate(benign, blocks) or math.nan,
        )
    if dataset == "harmbench":
        harmful = [True] * len(rows)
        return miss_rate(harmful, blocks) or math.nan, math.nan
    harmful = [not r.is_benign_known and _is_harm_row(r) for r in rows]
    benign = [r.is_benign_known for r in rows]
    miss = miss_rate(harmful, blocks) if any(harmful) else math.nan
    fpr = false_positive_rate(benign, blocks) if any(benign) else math.nan
    return miss or math.nan, fpr or math.nan


def bootstrap_jbb_arms(
    rows: list[ExampleRecord],
    preds_by_arm: dict[str, dict[str, list[PredictionRecord]]],
    metrics: dict[str, Any],
) -> dict[str, Any]:
    harmful, benign = _jailbreakbench_harm_benign(rows)
    out: dict[str, Any] = {}
    for arm in MODEL_ARMS:
        blocks = model_blocks(
            "jailbreakbench", rows, preds_by_arm[arm]["jailbreakbench"], FIXED_THRESHOLD
        )
        miss_ind = [1.0 if h and not b else 0.0 for h, b in zip(harmful, blocks, strict=True) if h]
        fpr_ind = [1.0 if bn and b else 0.0 for bn, b in zip(benign, blocks, strict=True) if bn]
        out[f"{arm}_at_0_5"] = {
            "miss_rate": bootstrap_ci(miss_ind),
            "false_positive_rate": bootstrap_ci(fpr_ind),
        }
    guard = preds_by_arm[GUARDRAIL_ARM]["jailbreakbench"]
    cross_blocks = [
        band_blocks_at_strength(p.band or "NONE", STACK_STRENGTH) for p in guard
    ]
    sens_bands = _sensitivity_band_lookup(rows, guard)
    out["guardrail_pre_registered_medium"] = {
        "miss_rate": bootstrap_ci(
            [1.0 if h and not b else 0.0 for h, b in zip(harmful, cross_blocks, strict=True) if h]
        ),
        "false_positive_rate": bootstrap_ci(
            [1.0 if bn and b else 0.0 for bn, b in zip(benign, cross_blocks, strict=True) if bn]
        ),
    }
    for strength in ("low", "medium", "high"):
        blocks = [
            band_blocks_at_strength(sens_bands[r.example_id], strength) for r in rows
        ]
        out[f"guardrail_post_hoc_any_filter_{strength}"] = {
            "miss_rate": bootstrap_ci(
                [1.0 if h and not b else 0.0 for h, b in zip(harmful, blocks, strict=True) if h]
            ),
            "false_positive_rate": bootstrap_ci(
                [1.0 if bn and b else 0.0 for bn, b in zip(benign, blocks, strict=True) if bn]
            ),
        }
    # Cross-check against metrics JSON
    ref = metrics["arms"]["jev"]["jailbreakbench"]["primary"]
    recomputed = headline_miss_fpr_model(
        "jailbreakbench", rows, preds_by_arm["jev"]["jailbreakbench"], FIXED_THRESHOLD
    )
    out["_jev_miss_check"] = {"metrics_json": ref["miss_rate"], "recomputed": recomputed[0]}
    return out


def bootstrap_xstest_jev(
    rows: list[ExampleRecord],
    preds: list[PredictionRecord],
    tuned: float,
) -> dict[str, Any]:
    harmful = [bool(r.gold_labels.get("harmful")) for r in rows]  # type: ignore[union-attr]
    benign = [r.is_benign_known for r in rows]
    out: dict[str, Any] = {}
    for label, thr in (("tuned", tuned), ("at_0_5", FIXED_THRESHOLD)):
        blocks = model_blocks("xstest", rows, preds, thr)
        fpr_ind = [1.0 if bn and b else 0.0 for bn, b in zip(benign, blocks, strict=True) if bn]
        det_ind = [
            1.0 if h and b else 0.0 for h, b in zip(harmful, blocks, strict=True) if h
        ]
        out[label] = {
            "false_positive_rate_safe": bootstrap_ci(fpr_ind),
            "detection_rate_harmful": bootstrap_ci(det_ind),
        }
    return out


def agreement_metrics(
    dataset: str,
    rows: list[ExampleRecord],
    jev_preds: list[PredictionRecord],
    guard_preds: list[PredictionRecord],
    jev_threshold: float,
) -> dict[str, float]:
    jev_blocks = model_blocks(dataset, rows, jev_preds, jev_threshold)
    guard_blocks = [
        band_blocks_at_strength(p.band or "NONE", STACK_STRENGTH) for p in guard_preds
    ]
    return {
        "jaccard_block": jaccard_blocks(jev_blocks, guard_blocks),
        "cohens_kappa": cohens_kappa(jev_blocks, guard_blocks),
        "n": len(rows),
    }


def headline_miss_rate(arm: str, dataset: str, metrics: dict[str, Any]) -> float:
    """Headline harmful miss rate per arm and dataset (matches paper operating point)."""
    if dataset == "wildguardmix":
        if arm == GUARDRAIL_ARM:
            return float(metrics["arms"][arm][dataset]["miss_rate"])
        return float(metrics["stacks"][arm][dataset]["model_alone"]["miss_rate"])
    if dataset == "xstest":
        if arm == GUARDRAIL_ARM:
            return float(metrics["arms"][arm][dataset]["miss_rate"])
        primary = metrics["arms"][arm][dataset]["primary"]
        return 1.0 - float(primary["detection_rate_harmful"])
    if arm == GUARDRAIL_ARM:
        return float(metrics["arms"][arm][dataset]["miss_rate"])
    arm_ds = metrics["arms"][arm][dataset]
    if arm_ds.get("miss_rate") is not None:
        return float(arm_ds["miss_rate"])
    return float(arm_ds["primary"]["miss_rate"])


def headline_fpr(arm: str, dataset: str, metrics: dict[str, Any]) -> float:
    arm_ds = metrics["arms"][arm][dataset]
    primary = arm_ds.get("primary") or {}
    fpr = arm_ds.get("false_positive_rate") or primary.get("false_positive_rate")
    if fpr is None and dataset == "xstest":
        fpr = primary.get("false_positive_rate_safe")
    if fpr is None and dataset == "wildguardmix" and arm in MODEL_ARMS:
        fpr = metrics["stacks"][arm][dataset]["model_alone"]["false_positive_rate"]
    if fpr is None:
        return math.nan
    return float(fpr)


def _asymmetric_err(
    point: float, ci: dict[str, float]
) -> tuple[float, float]:
    return (point - ci["ci_low"], ci["ci_high"] - point)


def pareto_undominated(
    points: dict[str, tuple[float, float]],
) -> list[str]:
    arms = list(points.keys())
    undom: list[str] = []
    for a in arms:
        xa, ya = points[a]
        dominated = False
        for b in arms:
            if a == b:
                continue
            xb, yb = points[b]
            if xb <= xa and yb <= ya and (xb < xa or yb < ya):
                dominated = True
                break
        if not dominated:
            undom.append(a)
    return sorted(undom)


def fig_jbb_crosswalk(
    metrics: dict[str, Any],
    bootstrap_jbb: dict[str, Any],
    narrative: dict[str, Any],
) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    sens = metrics["post_hoc_sensitivity"]["jailbreakbench"]
    gbs = metrics.get("guardrail_by_strength", {})
    markers = {"low": "^", "medium": "s", "high": "D"}

    # Strength barely moves the pre-registered mapping (miss 1.00 / 0.98 / 0.96,
    # FPR 0). Those points share x=0, so draw the registered medium point and
    # state the three miss rates in an annotation. Do not call them equal.
    strength_miss = {
        strength: float(gbs[strength]["jailbreakbench"]["miss_rate"])
        for strength in ("low", "medium", "high")
        if gbs.get(strength, {}).get("jailbreakbench", {}).get("miss_rate") is not None
    }
    bs_cross = bootstrap_jbb["guardrail_pre_registered_medium"]
    if strength_miss:
        fpr_c = 0.0
        miss_c = strength_miss.get("medium", next(iter(strength_miss.values())))
        xlo, xhi = _asymmetric_err(fpr_c, bs_cross["false_positive_rate"])
        ylo, yhi = _asymmetric_err(miss_c, bs_cross["miss_rate"])
        ax.errorbar(
            fpr_c,
            miss_c,
            xerr=[[xlo], [xhi]],
            yerr=[[ylo], [yhi]],
            fmt="s",
            color=PALETTE["guardrails"],
            markersize=9,
            capsize=3,
            label="Pre-registered crosswalk (medium)",
            zorder=4,
        )
        ax.annotate(
            "Prompt Attack only, FPR 0\n"
            f"low {strength_miss.get('low', float('nan')):.2f}, "
            f"medium {strength_miss.get('medium', float('nan')):.2f}, "
            f"high {strength_miss.get('high', float('nan')):.2f}",
            (fpr_c, miss_c),
            textcoords="offset points",
            xytext=(10, -28),
            fontsize=7,
            color=PALETTE["guardrails"],
        )

    for strength, vals in sens.get("any_content_filter_max_band", {}).items():
        fpr = float(vals["false_positive_rate"])
        miss = float(vals["miss_rate"])
        bs = bootstrap_jbb.get(f"guardrail_post_hoc_any_filter_{strength}", {})
        xlo, xhi = _asymmetric_err(fpr, bs.get("false_positive_rate", {"ci_low": fpr, "ci_high": fpr}))
        ylo, yhi = _asymmetric_err(miss, bs.get("miss_rate", {"ci_low": miss, "ci_high": miss}))
        ax.errorbar(
            fpr,
            miss,
            xerr=[[xlo], [xhi]],
            yerr=[[ylo], [yhi]],
            fmt=markers.get(strength, "o"),
            markerfacecolor="none",
            markeredgecolor=PALETTE["post_hoc"],
            markeredgewidth=2,
            markersize=9,
            capsize=3,
            color=PALETTE["post_hoc"],
            label=f"Post-hoc any-filter ({strength})",
            zorder=3,
        )

    for arm in MODEL_ARMS:
        primary = metrics["arms"][arm]["jailbreakbench"]["threshold_0_5"]["primary"]
        fpr = float(primary["false_positive_rate"])
        miss = float(primary["miss_rate"])
        bs = bootstrap_jbb[f"{arm}_at_0_5"]
        xlo, xhi = _asymmetric_err(fpr, bs["false_positive_rate"])
        ylo, yhi = _asymmetric_err(miss, bs["miss_rate"])
        ax.errorbar(
            fpr,
            miss,
            xerr=[[xlo], [xhi]],
            yerr=[[ylo], [yhi]],
            fmt="o",
            color=PALETTE.get(arm, "#333333"),
            markersize=8,
            capsize=3,
            label=f"{arm} @ 0.5",
            zorder=5,
        )

    ax.set_xlabel("False-positive rate (benign)")
    ax.set_ylabel("Miss rate (harmful)")
    ax.set_title(
        "Category mapping sets the JailbreakBench miss.\nStrength barely moves it."
    )
    ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1), borderaxespad=0)
    fig.subplots_adjust(right=0.72)
    path = OUT_DIR / "jbb_crosswalk.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    narrative["figures"]["jbb_crosswalk"] = {
        "path": str(path.relative_to(EXPERIMENT_ROOT)),
        "crosswalk_strengths_collapsed": False,
        "crosswalk_miss_by_strength": strength_miss,
        "takeaway": (
            "Under the pre-registered Prompt Attack crosswalk, strength barely moves "
            "JailbreakBench guardrail miss (1.00 low, 0.98 medium, 0.96 high, FPR 0). "
            "A post-hoc any-filter rule at medium strength cuts miss to 0.23 at FPR 0.19. "
            "Jev at 0.5 stays near miss 0.03 and FPR 0.34."
        ),
    }


def fig_stack_frontier(metrics: dict[str, Any], narrative: dict[str, Any]) -> None:
    datasets = ["xstest", "wildguardmix"]
    stacks = metrics["stacks"]["jev"]
    policy_order = (
        "model_alone",
        "guardrail_alone",
        "union",
        "intersection",
        "cascade",
    )
    policy_labels = {
        "model_alone": "Jev alone",
        "guardrail_alone": "Guardrail alone",
        "union": "Union",
        "intersection": "Intersection",
        "cascade": "Cascade",
    }
    narrative["stack_policies"] = {ds: stacks[ds] for ds in datasets}

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), squeeze=False)
    for ax, dataset in zip(axes[0], datasets, strict=True):
        grouped: dict[tuple[float, float], list[str]] = {}
        for policy in policy_order:
            pt = stacks[dataset][policy]
            key = (round(float(pt["false_positive_rate"]), 4), round(float(pt["miss_rate"]), 4))
            grouped.setdefault(key, []).append(policy_labels[policy])
        for (fpr, miss), labels in grouped.items():
            ax.scatter(fpr, miss, s=70, color=PALETTE["jev"], zorder=3)
            ax.annotate(
                " = ".join(labels),
                (fpr, miss),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=7,
                ha="left",
            )
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.set_title(dataset)
        ax.set_xlabel("False-positive rate (benign)")
        ax.set_ylabel("Miss rate (harmful)")
    fig.suptitle("Stacks move the frontier only when the guardrail still catches harm")
    fig.tight_layout()
    path = OUT_DIR / "stack_frontier.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    narrative["figures"]["stack_frontier"] = {
        "path": str(path.relative_to(EXPERIMENT_ROOT)),
        "datasets_paneled": datasets,
        "jailbreakbench_excluded": (
            "JailbreakBench omitted: guardrail-alone miss ~0.98 under the pre-registered crosswalk."
        ),
        "takeaway": (
            "On XSTest, union cuts harmful miss from 0.16 to 0.10 at the same FPR 0.012, and "
            "cascade sits between them (miss 0.125). On WildGuardMix, cascade equals Jev alone "
            "(miss 0.671, FPR 0.192); union lowers miss to 0.366 and raises FPR to 0.538. "
            "JailbreakBench is omitted because guardrail-alone miss is 0.98."
        ),
    }


def fig_cost_vs_miss(metrics: dict[str, Any], narrative: dict[str, Any]) -> None:
    latency = metrics["latency_cost"]
    arms = ("jev", "clef", "clef-flash", GUARDRAIL_ARM)
    panels = ["jailbreakbench", "xstest", "wildguardmix", "harmbench"]
    fig, axes = plt.subplots(2, 2, figsize=(9, 7), squeeze=False)
    panel_points: dict[str, dict[str, dict[str, float]]] = {}
    for idx, dataset in enumerate(panels):
        ax = axes[idx // 2][idx % 2]
        panel_points[dataset] = {}
        for arm in arms:
            cost = float(latency[arm]["cost_per_1000_prompts_usd"])
            miss = headline_miss_rate(arm, dataset, metrics)
            panel_points[dataset][arm] = {"cost_per_1000": cost, "miss_rate": miss}
            ax.scatter(
                cost,
                miss,
                s=90,
                color=PALETTE.get(arm, "#333"),
                label=arm if idx == 0 else None,
            )
            ax.annotate(arm, (cost, miss), textcoords="offset points", xytext=(4, 4), fontsize=7)
        ax.set_xlim(0, 0.26)
        ax.set_title(dataset, fontsize=10)
        ax.set_xlabel("USD / 1k prompts (arm-level)")
        ax.set_ylabel("Miss rate @ headline")
    axes[0][0].legend(fontsize=7, loc="lower right")
    fig.suptitle("Jev is cheapest and not always lowest-miss")
    fig.tight_layout()
    path = OUT_DIR / "cost_vs_miss.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    narrative["cost_vs_miss_points"] = panel_points
    narrative["figures"]["cost_vs_miss"] = {
        "path": str(path.relative_to(EXPERIMENT_ROOT)),
        "cost_note": "Per-arm cost_per_1000_prompts_usd from metrics JSON (not per-dataset).",
        "takeaway": (
            "Jev is cheapest (~$0.023/1k) but not always lowest-miss—e.g. WildGuardMix Jev "
            "model-alone miss ~0.67 versus guardrails ~0.42 at headline thresholds."
        ),
    }


def fig_complementarity(
    metrics: dict[str, Any],
    rows_by_ds: dict[str, list[ExampleRecord]],
    preds: dict[str, dict[str, list[PredictionRecord]]],
    narrative: dict[str, Any],
) -> None:
    datasets = ["harmbench", "xstest"]
    wgm_rows = rows_by_ds.get("wildguardmix", [])
    if wgm_rows:
        has_both = any(
            bool(r.gold_labels.get("prompt_harm")) for r in wgm_rows  # type: ignore[union-attr]
        ) and any(not bool(r.gold_labels.get("prompt_harm")) for r in wgm_rows)  # type: ignore[union-attr]
        if has_both:
            datasets.append("wildguardmix")
    thresholds = metrics["thresholds"]["jev"]
    fig, axes = plt.subplots(1, len(datasets), figsize=(4 * len(datasets), 4), squeeze=False)
    comp_out: dict[str, Any] = {}
    labels = ["neither_miss", "jev_only", "guard_only", "both_miss"]
    colors = ["#0072B2", "#56B4E9", "#CC79A7", "#D55E00"]
    for ax, dataset in zip(axes[0], datasets, strict=True):
        rows = rows_by_ds[dataset]
        jev_b = model_blocks(dataset, rows, preds["jev"][dataset], thresholds[dataset])
        guard_b = [
            band_blocks_at_strength(p.band or "NONE", STACK_STRENGTH)
            for p in preds[GUARDRAIL_ARM][dataset]
        ]
        if dataset == "xstest":
            harmful_idx = [i for i, r in enumerate(rows) if bool(r.gold_labels.get("harmful"))]  # type: ignore[union-attr]
        elif dataset == "wildguardmix":
            harmful_idx = [
                i
                for i, r in enumerate(rows)
                if bool(r.gold_labels.get("prompt_harm"))  # type: ignore[union-attr]
            ]
        else:
            harmful_idx = list(range(len(rows)))
        counts = {k: 0 for k in labels}
        for i in harmful_idx:
            j, g = jev_b[i], guard_b[i]
            missed_j = not j
            missed_g = not g
            if not missed_j and not missed_g:
                counts["neither_miss"] += 1
            elif missed_j and not missed_g:
                counts["jev_only"] += 1
            elif not missed_j and missed_g:
                counts["guard_only"] += 1
            else:
                counts["both_miss"] += 1
        n = len(harmful_idx) or 1
        fracs = [counts[k] / n for k in labels]
        comp_out[dataset] = {"counts": counts, "fractions": dict(zip(labels, fracs)), "n_harmful": len(harmful_idx)}
        ax.bar(range(4), fracs, color=colors)
        ax.set_xticks(
            range(4),
            ["Both block", "Jev only", "Guardrail only", "Both miss"],
            rotation=25,
            ha="right",
            fontsize=8,
        )
        ax.set_ylim(0, 1)
        ax.set_title(dataset)
        ax.set_ylabel("Fraction of harmful items")
    fig.tight_layout()
    path = OUT_DIR / "complementarity.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    narrative["complementarity"] = comp_out
    narrative["figures"]["complementarity"] = {
        "path": str(path.relative_to(EXPERIMENT_ROOT)),
        "takeaway": (
            "Where the guardrail is informative, Jev and guardrails fail on different harmful "
            "items; 'guard only' and 'jev only' slices are non-trivial on HarmBench and XSTest."
        ),
    }


def fig_operating_points(
    rows_by_ds: dict[str, list[ExampleRecord]],
    preds: dict[str, dict[str, list[PredictionRecord]]],
    metrics: dict[str, Any],
    narrative: dict[str, Any],
) -> None:
    datasets = ("xstest", "wildguardmix")
    arms = ("jev", "clef")
    fig, axes = plt.subplots(len(datasets), 2, figsize=(10, 8))
    sweep_store: dict[str, Any] = {}
    for row_i, dataset in enumerate(datasets):
        rows = rows_by_ds[dataset]
        if dataset == "xstest":
            golds = [bool(r.gold_labels.get("harmful")) for r in rows]  # type: ignore[union-attr]
            benign = [r.is_benign_known for r in rows]
        else:
            golds = [bool(r.gold_labels.get("prompt_harm")) for r in rows]  # type: ignore[union-attr]
            benign = [not g for g in golds]
        ts = [i / 100 for i in range(101)]
        for col, arm in enumerate(arms):
            ax = axes[row_i][col]
            pred_list = preds[arm][dataset]
            probs = [harm_score(dataset, r, p) or 0.0 for r, p in zip(rows, pred_list)]
            misses = []
            fprs = []
            f1s = []
            for t in ts:
                blocks = [p >= t for p in probs]
                misses.append(miss_rate(golds, blocks) or 0.0)
                fprs.append(false_positive_rate(benign, blocks) or 0.0)
                f1s.append(binary_f1(golds, [{"noul": p} for p in probs], t))
            ax.plot(ts, misses, label="miss", color=PALETTE[arm])
            ax.plot(ts, fprs, label="FPR", color=PALETTE[arm], linestyle="--", alpha=0.7)
            ax.plot(ts, f1s, label="F1", color=PALETTE[arm], linestyle=":", alpha=0.8)
            tuned = metrics["thresholds"][arm][dataset]
            for t_mark, name in ((FIXED_THRESHOLD, "0.5"), (tuned, "tuned")):
                ax.axvline(t_mark, color="gray", linestyle=":", linewidth=1)
                ax.text(t_mark, 0.02, name, rotation=90, fontsize=7, va="bottom")
            ax.set_title(f"{dataset} — {arm}")
            ax.set_xlabel("Threshold")
            ax.legend(fontsize=7)
            sweep_store[f"{dataset}_{arm}"] = {
                "tuned_threshold": tuned,
                "miss_at_tuned": misses[int(round(tuned * 100))],
                "fpr_at_tuned": fprs[int(round(tuned * 100))],
                "f1_at_tuned": f1s[int(round(tuned * 100))],
            }
    fig.suptitle("Threshold sweeps (headline F1 uses harmful class)")
    fig.tight_layout()
    path = OUT_DIR / "operating_points.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    narrative["threshold_sweeps"] = sweep_store
    xst_primary = metrics["arms"]["jev"]["xstest"]["primary"]
    xst_half = metrics["arms"]["jev"]["xstest"]["threshold_0_5"]["primary"]
    tuned_thr = metrics["thresholds"]["jev"]["xstest"]
    miss_half = 1.0 - float(xst_half["detection_rate_harmful"])
    miss_tuned = 1.0 - float(xst_primary["detection_rate_harmful"])
    narrative["xstest_jev_threshold_tradeoff"] = {
        "threshold_0_5": {
            "false_positive_rate_safe": float(xst_half["false_positive_rate_safe"]),
            "harmful_miss_rate": miss_half,
        },
        "threshold_tuned": {
            "threshold": tuned_thr,
            "false_positive_rate_safe": float(xst_primary["false_positive_rate_safe"]),
            "harmful_miss_rate": miss_tuned,
        },
    }
    narrative["figures"]["operating_points"] = {
        "path": str(path.relative_to(EXPERIMENT_ROOT)),
        "takeaway": (
            f"As Jev's threshold rises from 0.5 to {tuned_thr:.2f}, XSTest benign FPR falls "
            f"from {float(xst_half['false_positive_rate_safe']):.3f} to "
            f"{float(xst_primary['false_positive_rate_safe']):.3f} while harmful miss rises "
            f"from {miss_half:.3f} to {miss_tuned:.2f}; on WildGuardMix, increasing the "
            "threshold lowers both harmful F1 and benign FPR (no FPR-rise trade)."
        ),
    }


def reliability_bins(golds: list[bool], probs: list[float], n_bins: int = 15) -> tuple[list[float], list[float]]:
    bins_acc: list[list[float]] = [[] for _ in range(n_bins)]
    for g, p in zip(golds, probs, strict=True):
        p = min(max(p, 0.0), 1.0)
        idx = min(int(p * n_bins), n_bins - 1)
        bins_acc[idx].append(float(g))
    xs = [(i + 0.5) / n_bins for i in range(n_bins)]
    ys = [
        (sum(bins_acc[i]) / len(bins_acc[i]) if bins_acc[i] else math.nan)
        for i in range(n_bins)
    ]
    return xs, ys


def fig_reliability(
    rows_by_ds: dict[str, list[ExampleRecord]],
    preds: dict[str, dict[str, list[PredictionRecord]]],
    narrative: dict[str, Any],
) -> None:
    panels: list[tuple[str, str]] = [
        ("toxigen", "toxic"),
        ("toxicchat", "toxic"),
        ("xstest", "harmful"),
    ]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.5 * len(panels), 4.2), squeeze=False)
    ece_out: dict[str, Any] = {}
    for ax, (dataset, key) in zip(axes[0], panels, strict=True):
        rows = rows_by_ds[dataset]
        for arm in ("jev", "clef"):
            pred_list = preds[arm][dataset]
            if dataset == "xstest":
                golds = [bool(r.gold_labels.get("harmful")) for r in rows]  # type: ignore[union-attr]
                probs = [harm_score(dataset, r, p) or 0.0 for r, p in zip(rows, pred_list)]
            else:
                golds = [bool(r.gold_labels[key]) for r in rows]  # type: ignore[index]
                probs = [harm_score(dataset, r, p) or 0.0 for r, p in zip(rows, pred_list)]
            ece = ece_score(golds, probs, 15)
            xs, ys = reliability_bins(golds, probs)
            ax.plot(xs, ys, marker="o", label=f"{arm} ECE={ece:.3f}", color=PALETTE[arm])
            ece_out[f"{dataset}_{arm}"] = ece
        ax.plot([0, 1], [0, 1], "k--", alpha=0.35)
        ax.set_title(dataset)
        ax.set_xlabel("Predicted P(harmful)")
        ax.set_ylabel("Empirical frequency")
        ax.legend(fontsize=8)
    fig.suptitle("Reliability diagrams (binary harm heads)")
    fig.tight_layout()
    path = OUT_DIR / "reliability.png"
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    narrative["ece"] = ece_out
    usable = all(v < 0.15 for v in ece_out.values())
    narrative["figures"]["reliability"] = {
        "path": str(path.relative_to(EXPERIMENT_ROOT)),
        "takeaway": (
            "Jev and Clef probabilities are moderately miscalibrated on these heads "
            f"(ECE roughly {min(ece_out.values()):.2f}–{max(ece_out.values()):.2f}); "
            + (
                "treat scores as ranking signals more than calibrated risks."
                if not usable
                else "some heads are usable as coarse risk scores."
            )
        ),
    }


def harmbench_miss_by_config(
    rows: list[ExampleRecord],
    preds: dict[str, dict[str, list[PredictionRecord]]],
    thresholds: dict[str, dict[str, float]],
) -> dict[str, Any]:
    configs = ("DirectRequest", "HumanJailbreaks")
    out: dict[str, Any] = {}
    for cfg in configs:
        idx = [j for j, r in enumerate(rows) if r.metadata.get("config") == cfg]
        n = len(idx)
        out[cfg] = {"n": n, "by_arm": {}}
        harmful = [True] * n
        for arm in (*MODEL_ARMS, GUARDRAIL_ARM):
            if arm == GUARDRAIL_ARM:
                blocks = [
                    band_blocks_at_strength(p.band or "NONE", STACK_STRENGTH)
                    for p in [preds[arm]["harmbench"][j] for j in idx]
                ]
            else:
                blocks = model_blocks(
                    "harmbench",
                    [rows[j] for j in idx],
                    [preds[arm]["harmbench"][j] for j in idx],
                    thresholds[arm]["harmbench"],
                )
            miss = miss_rate(harmful, blocks) or math.nan
            out[cfg]["by_arm"][arm] = {"miss_rate": float(miss), "n": n}
    return out


def fig_harm_splits(
    metrics: dict[str, Any],
    rows: list[ExampleRecord],
    preds: dict[str, dict[str, list[PredictionRecord]]],
    narrative: dict[str, Any],
) -> None:
    configs = ("DirectRequest", "HumanJailbreaks")
    thresholds = metrics["thresholds"]
    by_config = harmbench_miss_by_config(rows, preds, thresholds)
    narrative["harmbench_by_config"] = by_config

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    ax = axes[0]
    x = np.arange(len(configs))
    width = 0.25
    for i, arm in enumerate((*MODEL_ARMS, GUARDRAIL_ARM)):
        misses = []
        ci_low = []
        ci_high = []
        for cfg in configs:
            idx = [j for j, r in enumerate(rows) if r.metadata.get("config") == cfg]
            if arm == GUARDRAIL_ARM:
                blocks = [
                    band_blocks_at_strength(p.band or "NONE", STACK_STRENGTH)
                    for p in [preds[arm]["harmbench"][j] for j in idx]
                ]
            else:
                blocks = model_blocks(
                    "harmbench",
                    [rows[j] for j in idx],
                    [preds[arm]["harmbench"][j] for j in idx],
                    thresholds[arm]["harmbench"],
                )
            ind = [1.0 if not b else 0.0 for b in blocks]
            bs = bootstrap_ci(ind)
            misses.append(bs["mean"])
            ci_low.append(bs["ci_low"])
            ci_high.append(bs["ci_high"])
        err = [
            [misses[j] - ci_low[j] for j in range(len(configs))],
            [ci_high[j] - misses[j] for j in range(len(configs))],
        ]
        ax.bar(
            x + (i - 1.5) * width,
            misses,
            width,
            yerr=err,
            capsize=3,
            label=arm,
            color=PALETTE.get(arm, "#666"),
        )
    ax.set_xticks(x, configs)
    ax.set_ylabel("Miss rate (harmful)")
    ax.set_title("HarmBench by config")
    ax.legend(fontsize=7)
    ax2 = axes[1]
    dna = metrics.get("do_not_answer_aggregates", {}).get("detection_rate_by_risk_area", {})
    if dna:
        risks = sorted({k.split("|", 1)[1] for k in dna if "|" in k})
        gaps = []
        for risk in risks:
            j = dna.get(f"jev|{risk}", math.nan)
            g = dna.get(f"guardrails|{risk}", math.nan)
            if not math.isnan(j) and not math.isnan(g):
                gaps.append((abs(j - g), risk))
        gaps.sort(reverse=True)
        show = [r for _, r in gaps[:8]] or risks[:8]
        y2 = np.arange(len(show))
        jev_rates = [dna.get(f"jev|{r}", math.nan) for r in show]
        gr_rates = [dna.get(f"guardrails|{r}", math.nan) for r in show]
        ax2.barh(y2 - 0.15, jev_rates, height=0.3, label="Jev", color=PALETTE["jev"])
        ax2.barh(y2 + 0.15, gr_rates, height=0.3, label="Guardrails", color=PALETTE["guardrails"])
        ax2.set_yticks(y2, show, fontsize=8)
        ax2.set_xlabel("Detection rate")
        ax2.set_title("Do-Not-Answer detection by risk area")
        ax2.legend(fontsize=7, loc="lower right")
    else:
        ax2.text(0.5, 0.5, "No DNA aggregates in metrics", ha="center")
        ax2.axis("off")
    fig.tight_layout()
    path = OUT_DIR / "harm_splits.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    dr_jev = by_config["DirectRequest"]["by_arm"]["jev"]["miss_rate"]
    dr_gr = by_config["DirectRequest"]["by_arm"]["guardrails"]["miss_rate"]
    hj_jev = by_config["HumanJailbreaks"]["by_arm"]["jev"]["miss_rate"]
    hj_gr = by_config["HumanJailbreaks"]["by_arm"]["guardrails"]["miss_rate"]
    narrative["figures"]["harm_splits"] = {
        "path": str(path.relative_to(EXPERIMENT_ROOT)),
        "takeaway": (
            f"HarmBench miss reverses by config: guardrails miss more than Jev on DirectRequest "
            f"({dr_gr:.3f} vs {dr_jev:.3f}, n={by_config['DirectRequest']['n']}) but less on "
            f"HumanJailbreaks ({hj_gr:.3f} vs {hj_jev:.3f}, n={by_config['HumanJailbreaks']['n']}), "
            "so the ~0.203 overall guardrail miss is not uniform."
        ),
    }


def pareto_notes(metrics: dict[str, Any]) -> dict[str, Any]:
    latency = metrics["latency_cost"]
    arms = ("jev", "clef", "clef-flash", GUARDRAIL_ARM)
    out: dict[str, Any] = {}
    for dataset in ("jailbreakbench", "xstest", "wildguardmix", "harmbench"):
        miss_cost: dict[str, tuple[float, float]] = {}
        miss_fpr: dict[str, tuple[float, float]] = {}
        for arm in arms:
            miss = headline_miss_rate(arm, dataset, metrics)
            fpr = headline_fpr(arm, dataset, metrics)
            cost = float(latency[arm]["cost_per_1000_prompts_usd"])
            miss_cost[arm] = (miss, cost)
            if not math.isnan(fpr):
                miss_fpr[arm] = (miss, fpr)
        out[dataset] = {
            "undominated_miss_cost": pareto_undominated(miss_cost),
            "undominated_miss_fpr": pareto_undominated(miss_fpr),
            "points_miss_cost": {a: {"miss": v[0], "cost": v[1]} for a, v in miss_cost.items()},
            "points_miss_fpr": {a: {"miss": v[0], "fpr": v[1]} for a, v in miss_fpr.items()},
        }
    return out


def verification_checks(metrics: dict[str, Any], narrative: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    tol = 0.01
    refs = {
        "xstest_jev_fpr_tuned": (0.0120, metrics["arms"]["jev"]["xstest"]["primary"]["false_positive_rate_safe"]),
        "xstest_jev_fpr_0_5": (0.0840, metrics["arms"]["jev"]["xstest"]["threshold_0_5"]["primary"]["false_positive_rate_safe"]),
        "jbb_jev_miss": (0.0300, metrics["arms"]["jev"]["jailbreakbench"]["primary"]["miss_rate"]),
        "jbb_jev_fpr": (0.3400, metrics["arms"]["jev"]["jailbreakbench"]["primary"]["false_positive_rate"]),
        "jbb_guard_miss": (0.9800, metrics["arms"]["guardrails"]["jailbreakbench"]["miss_rate"]),
        "jbb_posthoc_medium_miss": (
            0.2300,
            metrics["post_hoc_sensitivity"]["jailbreakbench"]["any_content_filter_max_band"]["medium"]["miss_rate"],
        ),
        "jbb_posthoc_medium_fpr": (
            0.1900,
            metrics["post_hoc_sensitivity"]["jailbreakbench"]["any_content_filter_max_band"]["medium"]["false_positive_rate"],
        ),
        "harmbench_guard_miss": (0.2026, metrics["arms"]["guardrails"]["harmbench"]["miss_rate"]),
        "harmbench_jev_miss": (0.2870, metrics["arms"]["jev"]["harmbench"]["primary"]["miss_rate"]),
        "jev_cost_per_1k": (0.023, metrics["latency_cost"]["jev"]["cost_per_1000_prompts_usd"]),
        "jev_median_latency_ms": (88.9, metrics["latency_cost"]["jev"]["median_latency_ms"]),
    }
    mismatches = []
    for name, (expected, observed) in refs.items():
        if name == "jev_median_latency_ms":
            ok = abs(expected - observed) <= 0.1
            note = "RESULTS rounds 88.866 ms to 88.9 ms"
        else:
            ok = abs(expected - observed) <= tol
            note = None
        checks[name] = {
            "expected": expected,
            "observed": observed,
            "within_tol": ok,
            "note": note,
        }
        if not ok:
            mismatches.append(name)
    narrative["verification"] = checks
    narrative["verification_mismatches"] = mismatches
    return checks


def main() -> None:
    if "SCORER" in sys.argv:
        raise SystemExit("refusing to run scorers")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11})
    metrics = _load_metrics()
    datasets_needed = [
        "jailbreakbench",
        "xstest",
        "wildguardmix",
        "harmbench",
        "toxigen",
        "toxicchat",
    ]
    preds = _load_all_predictions(datasets_needed)
    rows_by_ds = {ds: _load_records(ds) for ds in datasets_needed}

    narrative: dict[str, Any] = {
        "run_id": RUN_ID,
        "figures": {},
        "bootstrap": {},
        "agreement": {},
        "pareto": {},
    }

    narrative["bootstrap"]["jailbreakbench"] = bootstrap_jbb_arms(
        rows_by_ds["jailbreakbench"],
        preds,
        metrics,
    )
    narrative["bootstrap"]["xstest_jev"] = bootstrap_xstest_jev(
        rows_by_ds["xstest"],
        preds["jev"]["xstest"],
        metrics["thresholds"]["jev"]["xstest"],
    )

    for ds in ("xstest", "wildguardmix", "jailbreakbench", "harmbench"):
        narrative["agreement"][ds] = agreement_metrics(
            ds,
            rows_by_ds[ds],
            preds["jev"][ds],
            preds[GUARDRAIL_ARM][ds],
            metrics["thresholds"]["jev"][ds],
        )

    narrative["pareto"] = pareto_notes(metrics)
    verification_checks(metrics, narrative)

    fig_jbb_crosswalk(metrics, narrative["bootstrap"]["jailbreakbench"], narrative)
    fig_stack_frontier(metrics, narrative)
    fig_cost_vs_miss(metrics, narrative)
    fig_complementarity(metrics, rows_by_ds, preds, narrative)
    fig_operating_points(rows_by_ds, preds, metrics, narrative)
    fig_reliability(rows_by_ds, preds, narrative)
    fig_harm_splits(metrics, rows_by_ds["harmbench"], preds, narrative)

    out_json = OUT_DIR / "narrative_metrics.json"
    out_json.write_text(json.dumps(narrative, indent=2), encoding="utf-8")
    print(f"wrote {out_json}")
    for name, meta in narrative["figures"].items():
        p = EXPERIMENT_ROOT / meta["path"]
        size = p.stat().st_size if p.is_file() else 0
        print(f"  {name}: {size} bytes")


if __name__ == "__main__":
    main()
