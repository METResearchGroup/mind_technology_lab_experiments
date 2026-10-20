"""Score datasets with one arm and run Jev harness checks (step 4).

Run from the experiment folder:

    uv run python scripts/run_score.py --arm jev \\
        --datasets toxigen,openai_moderation,toxicchat,prompt_injections,go_emotions,emotion
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.cache import ResponseCache, REVISION_MANIFEST  # noqa: E402
from shared.metrics import (  # noqa: E402
    HARNESS_SPECS,
    HarnessSpec,
    check_harness_value,
    compute_dataset_metrics,
    format_interval,
)
from shared.records import ExampleRecord, PredictionRecord, QuestionItem, QuestionSpec  # noqa: E402
from scorers.jev import JevScorer  # noqa: E402

TEMPLATE_DIR = EXPERIMENT_ROOT / "data" / "templates"
STUDY_CONFIG = EXPERIMENT_ROOT / "configs" / "study.json"
PROGRESS_LOG = EXPERIMENT_ROOT / "cache" / "run_score_progress.log"

HARNESS_DATASETS: dict[str, dict[str, str]] = {
    "toxigen": {"module": "datasets.toxigen", "split": "test"},
    "openai_moderation": {"module": "datasets.openai_moderation", "split": "train"},
    "toxicchat": {"module": "datasets.toxicchat", "split": "test"},
    "prompt_injections": {"module": "datasets.prompt_injections", "split": "test"},
    "go_emotions": {"module": "datasets.go_emotions", "split": "test"},
    "emotion": {"module": "datasets.emotion", "split": "test"},
}

RATE_LIMIT_MARKERS = ("rate limit", "429", "too many requests", "throttl")
MAX_SCORE_RETRIES = 6
RETRY_BASE_SECONDS = 2.0
MAX_WORKERS = 8


@dataclass
class MetricResult:
    spec: HarnessSpec
    observed: float
    passed: bool


def main() -> None:
    args = _parse_args()
    if args.arm != "jev":
        raise SystemExit("step 4 supports --arm jev only")
    datasets = [name.strip() for name in args.datasets.split(",") if name.strip()]
    unknown = [name for name in datasets if name not in HARNESS_DATASETS]
    if unknown:
        raise SystemExit(f"unsupported datasets for harness: {unknown}")

    template_versions = {
        name: _template_file_hash(name) for name in datasets
    }
    dataset_revisions = _read_dataset_revisions()
    run_id = args.run_id or _allocate_run_id(
        dataset_revisions, template_versions, arms=["jev"]
    )

    print(f"run_id={run_id}")
    print("row counts (before scoring):")
    records_by_dataset: dict[str, list[ExampleRecord]] = {}
    for name in datasets:
        cfg = HARNESS_DATASETS[name]
        records = _load_records(name, cfg["split"])
        records_by_dataset[name] = records
        print(f"  {name}\t{cfg['split']}\t{len(records)}")

    cache = ResponseCache()
    cache_lock = threading.Lock()
    progress_lock = threading.Lock()
    model_version = _model_version("jev")
    total_billed = 0.0
    provider_calls = 0

    predictions_by_dataset: dict[str, list[PredictionRecord]] = {}

    for dataset in datasets:
        records = records_by_dataset[dataset]
        question, template_version = load_question(dataset)
        if template_version != template_versions[dataset]:
            raise SystemExit(f"template hash mismatch for {dataset}")
        preds, new_calls, new_billed = _score_dataset(
            records,
            question,
            template_version,
            arm=args.arm,
            model_version=model_version,
            cache=cache,
            cache_lock=cache_lock,
            progress_lock=progress_lock,
            dataset=dataset,
            run_id=run_id,
        )
        predictions_by_dataset[dataset] = preds
        total_billed += new_billed
        provider_calls += new_calls
        _write_predictions(run_id, args.arm, dataset, preds)
        print(f"scored {dataset}: rows={len(preds)} new_provider_calls={new_calls}")

    manifest_path = _write_manifest(
        run_id,
        arms=["jev"],
        model_version=model_version,
        datasets=datasets,
        records_by_dataset=records_by_dataset,
        template_versions=template_versions,
        dataset_revisions=dataset_revisions,
        threshold=args.threshold,
    )
    print(f"manifest: {manifest_path}")

    metric_results = _evaluate_harness(
        datasets, records_by_dataset, predictions_by_dataset, threshold=args.threshold
    )
    all_pass = all(row.passed for row in metric_results)
    _print_metric_summary(metric_results)
    _update_results_md(run_id, metric_results, all_pass)

    price_per_m = float(
        json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
        .get("prices_usd", {})
        .get("jev_per_million_input_tokens", 0.042)
    )
    usd = total_billed / 1_000_000 * price_per_m
    print(
        f"billed_units={total_billed:.0f} "
        f"estimated_usd={usd:.4f} ({total_billed:.0f} * {price_per_m}/1e6)"
    )
    print(f"harness {'PASS' if all_pass else 'FAIL'}")
    raise SystemExit(0 if all_pass else 1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score datasets and run harness checks.")
    parser.add_argument("--arm", required=True, choices=["jev", "clef", "clef-flash", "guardrails"])
    parser.add_argument("--datasets", required=True, help="Comma-separated dataset short names.")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--threshold", type=float, default=0.5)
    return parser.parse_args()


def _load_records(dataset: str, split: str) -> list[ExampleRecord]:
    module_name = HARNESS_DATASETS[dataset]["module"]
    module = importlib.import_module(module_name)
    return module.load_records(split)


def load_question(dataset: str) -> tuple[QuestionSpec, str]:
    path = TEMPLATE_DIR / f"{dataset}.json"
    if not path.is_file():
        raise SystemExit(f"missing template: {path}")
    raw_bytes = path.read_bytes()
    template_version = hashlib.sha256(raw_bytes).hexdigest()
    flat = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(flat, dict):
        raise SystemExit(f"template {path} is not a JSON object")
    questions = {
        head_id: QuestionItem.model_validate(spec) for head_id, spec in flat.items()
    }
    return QuestionSpec(questions=questions), template_version


def _template_file_hash(dataset: str) -> str:
    path = TEMPLATE_DIR / f"{dataset}.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_dataset_revisions() -> dict[str, str]:
    if not REVISION_MANIFEST.is_file():
        return {}
    payload = json.loads(REVISION_MANIFEST.read_text(encoding="utf-8"))
    return {str(key): str(entry.get("revision", "")) for key, entry in payload.items()}


def _allocate_run_id(
    dataset_revisions: dict[str, str],
    template_versions: dict[str, str],
    *,
    arms: list[str],
) -> str:
    parts = [
        "arms=" + ",".join(sorted(arms)),
        "revisions=" + json.dumps(dataset_revisions, sort_keys=True),
        "templates=" + json.dumps(template_versions, sort_keys=True),
    ]
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{digest}"


def _model_version(arm: str) -> str:
    payload = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    return str(payload.get("models", {}).get(arm, arm))


def _score_dataset(
    records: list[ExampleRecord],
    question: QuestionSpec,
    template_version: str,
    *,
    arm: str,
    model_version: str,
    cache: ResponseCache,
    cache_lock: threading.Lock,
    progress_lock: threading.Lock,
    dataset: str,
    run_id: str,
) -> tuple[list[PredictionRecord], int, float]:
    keys = [
        ResponseCache.cache_key(arm, model_version, template_version, row.example_id)
        for row in records
    ]
    predictions: list[PredictionRecord | None] = [None] * len(records)
    pending_indices: list[int] = []
    new_calls = 0
    new_billed = 0.0

    for index, (row, key) in enumerate(zip(records, keys, strict=True)):
        cached = cache.get(key)
        if cached is not None:
            predictions[index] = cached
        else:
            pending_indices.append(index)

    if pending_indices:
        print(f"{dataset}: cache hits={len(records) - len(pending_indices)} "
              f"misses={len(pending_indices)} workers={MAX_WORKERS}")

    def work(index: int) -> tuple[int, PredictionRecord, bool]:
        row = records[index]
        key = keys[index]
        scorer = JevScorer()
        prediction = _score_one_with_retry(scorer, row, question)
        prediction.template_version = template_version
        with cache_lock:
            cache.put(key, prediction)
        return index, prediction, True

    if pending_indices:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(work, idx): idx for idx in pending_indices}
            done = 0
            for future in as_completed(futures):
                index, prediction, _called = future.result()
                predictions[index] = prediction
                new_calls += 1
                new_billed += float(prediction.billed_units or 0.0)
                done += 1
                if done % 100 == 0 or done == len(pending_indices):
                    with progress_lock:
                        PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)
                        with PROGRESS_LOG.open("a", encoding="utf-8") as handle:
                            handle.write(
                                f"{run_id}\t{dataset}\tscored={done}\t"
                                f"pending={len(pending_indices)}\n"
                            )
                    print(f"{dataset}: progress {done}/{len(pending_indices)}")

    ordered = [p for p in predictions if p is not None]
    if len(ordered) != len(records):
        raise SystemExit(f"{dataset}: missing predictions after scoring")
    ordered.sort(key=lambda row: row.example_id)
    return ordered, new_calls, new_billed


def _score_one_with_retry(
    scorer: JevScorer, record: ExampleRecord, question: QuestionSpec
) -> PredictionRecord:
    delay = RETRY_BASE_SECONDS
    last_exc: Exception | None = None
    for attempt in range(MAX_SCORE_RETRIES):
        try:
            batch = scorer.score([record], question)
            if not batch:
                raise RuntimeError("empty scorer response")
            return batch[0]
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            message = str(exc).lower()
            if not any(marker in message for marker in RATE_LIMIT_MARKERS):
                raise
            if attempt + 1 >= MAX_SCORE_RETRIES:
                break
            time.sleep(delay)
            delay *= 2.0
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("score failed without exception")


def _write_predictions(
    run_id: str, arm: str, dataset: str, predictions: list[PredictionRecord]
) -> None:
    out_dir = EXPERIMENT_ROOT / "outputs" / "predictions" / run_id / arm
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"{dataset}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(row.model_dump_json())
            handle.write("\n")
    rows_payload = [row.model_dump() for row in predictions]
    for payload in rows_payload:
        raw = payload.get("raw_response")
        if isinstance(raw, dict):
            payload["raw_response"] = json.dumps(raw, sort_keys=True)
    frame = pd.DataFrame(rows_payload)
    parquet_path = out_dir / f"{dataset}.parquet"
    frame.to_parquet(parquet_path, index=False)
    print(f"wrote {len(predictions)} rows to {jsonl_path} and {parquet_path}")


def _write_manifest(
    run_id: str,
    *,
    arms: list[str],
    model_version: str,
    datasets: list[str],
    records_by_dataset: dict[str, list[ExampleRecord]],
    template_versions: dict[str, str],
    dataset_revisions: dict[str, str],
    threshold: float,
) -> Path:
    study = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    manifest = {
        "run_id": run_id,
        "arms": arms,
        "models": {"jev": model_version},
        "region": study.get("region", "us-east-2"),
        "prices_usd": study.get("prices_usd", {}),
        "threshold": threshold,
        "dataset_revisions": dataset_revisions,
        "template_versions": template_versions,
        "datasets": {
            name: {
                "split": HARNESS_DATASETS[name]["split"],
                "rows": len(records_by_dataset[name]),
            }
            for name in datasets
        },
    }
    out_dir = EXPERIMENT_ROOT / "outputs" / "manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_id}.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _evaluate_harness(
    datasets: list[str],
    records_by_dataset: dict[str, list[ExampleRecord]],
    predictions_by_dataset: dict[str, list[PredictionRecord]],
    *,
    threshold: float,
) -> list[MetricResult]:
    computed: dict[str, dict[str, float]] = {}
    for dataset in datasets:
        rows = records_by_dataset[dataset]
        preds = predictions_by_dataset[dataset]
        by_id = {row.example_id: row for row in preds}
        ordered_preds = [by_id[row.example_id] for row in rows]
        template_path = TEMPLATE_DIR / f"{dataset}.json"
        computed[dataset] = compute_dataset_metrics(
            dataset,
            rows,
            ordered_preds,
            threshold=threshold,
            template_path=template_path,
        )

    results: list[MetricResult] = []
    for spec in HARNESS_SPECS:
        if spec.dataset not in computed:
            continue
        metrics = computed[spec.dataset]
        if spec.metric_name not in metrics:
            raise SystemExit(
                f"missing metric {spec.metric_name} for dataset {spec.dataset}"
            )
        observed = metrics[spec.metric_name]
        passed = check_harness_value(spec, observed)
        results.append(MetricResult(spec=spec, observed=observed, passed=passed))
    return results


def _print_metric_summary(results: list[MetricResult]) -> None:
    for row in results:
        spec = row.spec
        interval = format_interval(spec)
        status = "PASS" if row.passed else "FAIL"
        print(
            f"{spec.dataset}\t{spec.metric_name}\t"
            f"published={spec.published:.3f}\tinterval={interval}\t"
            f"observed={row.observed:.4f}\t{status}"
        )


def _update_results_md(
    run_id: str, results: list[MetricResult], all_pass: bool
) -> None:
    path = EXPERIMENT_ROOT / "RESULTS.md"
    lines = [
        "# Results",
        "",
        "Step 3: smoke passed for `jev`, `clef`, and `clef-flash` (cache hit on "
        "rerun). Arm `guardrails` deferred to step 5.",
        "",
        "## Jev harness check (step 4)",
        "",
        f"Overall: **{'PASS' if all_pass else 'FAIL'}** (`run_id={run_id}`).",
        "",
        "| Dataset | Metric | Published | Interval | Observed | Status |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in results:
        spec = row.spec
        lines.append(
            f"| {spec.dataset} | {spec.metric_name} | {spec.published:.3f} | "
            f"{format_interval(spec)} | {row.observed:.4f} | "
            f"{'PASS' if row.passed else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            f"Predictions: `outputs/predictions/{run_id}/jev/`.",
            f"Manifest: `outputs/manifests/{run_id}.json`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
