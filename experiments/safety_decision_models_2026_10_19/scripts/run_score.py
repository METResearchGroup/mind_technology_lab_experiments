"""Score datasets with decision-model arms (step 4 harness or step 6 full pack).

Run from the experiment folder:

    uv run python scripts/run_score.py --arm all
    uv run python scripts/run_score.py --arm jev --harness \\
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
from collections.abc import Callable
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
from scorers.clef import ClefScorer, TRUNCATED_STATUS  # noqa: E402
from scorers.guardrails import GuardrailsScorer  # noqa: E402
from scorers.jev import JevScorer, MAX_TOKENS_ERROR  # noqa: E402

TEMPLATE_DIR = EXPERIMENT_ROOT / "data" / "templates"
STUDY_CONFIG = EXPERIMENT_ROOT / "configs" / "study.json"
PROGRESS_LOG = EXPERIMENT_ROOT / "cache" / "run_score_progress.log"

ALL_ARMS = ("jev", "clef", "clef-flash", "guardrails")
DATASET_ORDER = (
    "toxigen",
    "openai_moderation",
    "toxicchat",
    "prompt_injections",
    "wildguardmix",
    "do_not_answer",
    "xstest",
    "harmbench",
    "jailbreakbench",
    "go_emotions",
    "emotion",
)
DATASET_MODULES = {name: f"datasets.{name}" for name in DATASET_ORDER}

HARNESS_DATASETS: dict[str, dict[str, str]] = {
    "toxigen": {"module": "datasets.toxigen", "split": "test"},
    "openai_moderation": {"module": "datasets.openai_moderation", "split": "train"},
    "toxicchat": {"module": "datasets.toxicchat", "split": "test"},
    "prompt_injections": {"module": "datasets.prompt_injections", "split": "test"},
    "go_emotions": {"module": "datasets.go_emotions", "split": "test"},
    "emotion": {"module": "datasets.emotion", "split": "test"},
}

BUDGET_USD_CAP = 45.0
RATE_LIMIT_MARKERS = ("rate limit", "429", "too many requests", "throttl")
SERVER_ERROR_MARKERS = ("500", "502", "503", "504", "internal server error", "bad gateway")
MAX_SCORE_RETRIES = 6
RETRY_BASE_SECONDS = 2.0
MAX_WORKERS = 8


@dataclass
class MetricResult:
    spec: HarnessSpec
    observed: float
    passed: bool


@dataclass
class ArmBilling:
    arm: str
    new_provider_calls: int = 0
    billed_units: float = 0.0


def main() -> None:
    args = _parse_args()
    if args.harness:
        if args.arm != "jev":
            raise SystemExit("--harness requires --arm jev")
        _run_jev_harness(args)
        return
    arms = list(ALL_ARMS) if args.arm == "all" else [args.arm]
    datasets = _parse_datasets(args.datasets)
    _run_full_pack(arms, datasets, run_id=args.run_id)


def _parse_datasets(raw: str | None) -> list[str]:
    if not raw:
        return list(DATASET_ORDER)
    names = [name.strip() for name in raw.split(",") if name.strip()]
    unknown = [name for name in names if name not in DATASET_ORDER]
    if unknown:
        raise SystemExit(f"unsupported datasets: {unknown}")
    return names


def _run_full_pack(arms: list[str], datasets: list[str], *, run_id: str | None) -> None:
    study = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    template_versions = {name: _template_file_hash(name) for name in datasets}
    dataset_revisions = _read_dataset_revisions()
    run_id = run_id or _allocate_run_id(
        dataset_revisions, template_versions, arms=arms
    )
    print(f"run_id={run_id}")

    quota_note = _read_apply_guardrail_quota()
    manifest_path = _write_manifest(
        run_id,
        arms=arms,
        datasets=datasets,
        template_versions=template_versions,
        dataset_revisions=dataset_revisions,
        records_by_dataset={},
        billing_by_arm={},
        apply_guardrail_quota=quota_note,
        partial=True,
    )
    print(f"manifest (initial): {manifest_path}")

    print("row counts (before scoring):")
    records_by_dataset: dict[str, list[ExampleRecord]] = {}
    for name in datasets:
        try:
            records = _load_core_records(name)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"failed to load dataset {name}: {type(exc).__name__}: {exc}") from exc
        records_by_dataset[name] = records
        print(f"  {name}\t{len(records)}")

    cache = ResponseCache()
    cache_lock = threading.Lock()
    progress_lock = threading.Lock()
    billing_by_arm: dict[str, ArmBilling] = {arm: ArmBilling(arm=arm) for arm in arms}

    truncation_clef = 0
    truncation_clef_flash = 0
    jev_max_tokens = 0

    for arm in arms:
        model_version = _model_version(arm, study)
        print(f"\n=== arm {arm} model_version={model_version} ===")
        scorer_factory = _scorer_factory(arm)

        for dataset in datasets:
            records = records_by_dataset[dataset]
            question, template_version = load_question(dataset)
            if template_version != template_versions[dataset]:
                raise SystemExit(f"template hash mismatch for {dataset}")
            preds, new_calls, new_billed = _score_dataset(
                records,
                question,
                template_version,
                arm=arm,
                model_version=model_version,
                cache=cache,
                cache_lock=cache_lock,
                progress_lock=progress_lock,
                dataset=dataset,
                run_id=run_id,
                scorer_factory=scorer_factory,
            )
            billing_by_arm[arm].new_provider_calls += new_calls
            billing_by_arm[arm].billed_units += new_billed
            _write_predictions(run_id, arm, dataset, preds)
            print(
                f"scored {arm}/{dataset}: rows={len(preds)} "
                f"new_provider_calls={new_calls}"
            )
            for row in preds:
                if row.error_status == TRUNCATED_STATUS:
                    if arm == "clef":
                        truncation_clef += 1
                    elif arm == "clef-flash":
                        truncation_clef_flash += 1
                if arm == "jev" and row.error_status == MAX_TOKENS_ERROR:
                    jev_max_tokens += 1

        usd = _estimate_usd(arm, billing_by_arm[arm].billed_units, study)
        print(
            f"{arm} subtotal: billed_units={billing_by_arm[arm].billed_units:.0f} "
            f"new_calls={billing_by_arm[arm].new_provider_calls} "
            f"estimated_usd={usd:.4f}"
        )
        total_usd = sum(
            _estimate_usd(a, billing_by_arm[a].billed_units, study) for a in arms
        )
        if total_usd > BUDGET_USD_CAP:
            raise SystemExit(
                f"projected spend {total_usd:.2f} USD exceeds cap {BUDGET_USD_CAP}"
            )

    manifest_path = _write_manifest(
        run_id,
        arms=arms,
        datasets=datasets,
        template_versions=template_versions,
        dataset_revisions=dataset_revisions,
        records_by_dataset=records_by_dataset,
        billing_by_arm=billing_by_arm,
        apply_guardrail_quota=quota_note,
        partial=False,
    )
    print(f"manifest: {manifest_path}")

    print(
        f"truncated_rows clef={truncation_clef} clef-flash={truncation_clef_flash} "
        f"jev_max_tokens_exceeded={jev_max_tokens}"
    )
    for arm in arms:
        billed = billing_by_arm[arm].billed_units
        usd = _estimate_usd(arm, billed, study)
        price, unit = _price_line(arm, study)
        print(
            f"billing {arm}: billed_units={billed:.0f} "
            f"usd={usd:.4f} ({billed:.0f} * {price} {unit})"
        )


def _run_jev_harness(args: argparse.Namespace) -> None:
    datasets = [name.strip() for name in args.datasets.split(",") if name.strip()]
    unknown = [name for name in datasets if name not in HARNESS_DATASETS]
    if unknown:
        raise SystemExit(f"unsupported datasets for harness: {unknown}")

    template_versions = {name: _template_file_hash(name) for name in datasets}
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
            arm="jev",
            model_version=model_version,
            cache=cache,
            cache_lock=cache_lock,
            progress_lock=progress_lock,
            dataset=dataset,
            run_id=run_id,
            scorer_factory=lambda: JevScorer(),
        )
        predictions_by_dataset[dataset] = preds
        total_billed += new_billed
        provider_calls += new_calls
        _write_predictions(run_id, "jev", dataset, preds)
        print(f"scored {dataset}: rows={len(preds)} new_provider_calls={new_calls}")

    manifest_path = _write_manifest(
        run_id,
        arms=["jev"],
        datasets=datasets,
        template_versions=template_versions,
        dataset_revisions=dataset_revisions,
        records_by_dataset=records_by_dataset,
        billing_by_arm={"jev": ArmBilling("jev", provider_calls, total_billed)},
        apply_guardrail_quota=None,
        partial=False,
        harness=True,
        threshold=args.threshold,
    )
    print(f"manifest: {manifest_path}")

    metric_results = _evaluate_harness(
        datasets, records_by_dataset, predictions_by_dataset, threshold=args.threshold
    )
    all_pass = all(row.passed for row in metric_results)
    _print_metric_summary(metric_results)
    _update_results_md(run_id, metric_results, all_pass)

    study = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    price_per_m = float(study.get("prices_usd", {}).get("jev_per_million_input_tokens", 0.042))
    usd = total_billed / 1_000_000 * price_per_m
    print(
        f"billed_units={total_billed:.0f} "
        f"estimated_usd={usd:.4f} ({total_billed:.0f} * {price_per_m}/1e6)"
    )
    print(f"harness {'PASS' if all_pass else 'FAIL'}")
    raise SystemExit(0 if all_pass else 1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score datasets and optional harness.")
    parser.add_argument(
        "--arm",
        required=True,
        choices=["jev", "clef", "clef-flash", "guardrails", "all"],
    )
    parser.add_argument(
        "--datasets",
        default=None,
        help="Comma-separated dataset short names (default: all eleven).",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--harness",
        action="store_true",
        help="Run step-4 Jev harness on six overlapping datasets.",
    )
    return parser.parse_args()


def _load_core_records(dataset: str) -> list[ExampleRecord]:
    module = importlib.import_module(DATASET_MODULES[dataset])
    if dataset == "openai_moderation":
        return module.load_records("train")
    if dataset == "wildguardmix":
        return module.load_records()
    if dataset in ("xstest", "harmbench", "jailbreakbench", "do_not_answer"):
        return module.load_records()
    if dataset in ("toxigen", "toxicchat", "prompt_injections", "go_emotions", "emotion"):
        return module.load_records("test")
    return module.load_records()


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


def _model_version(arm: str, study: dict[str, Any] | None = None) -> str:
    payload = study or json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    if arm == "guardrails":
        return str(payload.get("guardrail_version", "") or payload.get("models", {}).get(arm, arm))
    return str(payload.get("models", {}).get(arm, arm))


def _scorer_factory(arm: str) -> Callable[[], Any]:
    if arm == "jev":
        return JevScorer
    if arm in ("clef", "clef-flash"):
        return lambda: ClefScorer(arm=arm)
    if arm == "guardrails":
        return GuardrailsScorer
    raise SystemExit(f"unknown arm {arm}")


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
    scorer_factory: Callable[[], Any],
) -> tuple[list[PredictionRecord], int, float]:
    keys = [
        ResponseCache.cache_key(arm, model_version, template_version, row.example_id)
        for row in records
    ]
    predictions: list[PredictionRecord | None] = [None] * len(records)
    pending_indices: list[int] = []
    new_calls = 0
    new_billed = 0.0

    for index, key in enumerate(keys):
        cached = cache.get(key)
        if cached is not None:
            predictions[index] = cached
        else:
            pending_indices.append(index)

    if pending_indices:
        print(
            f"{dataset}: cache hits={len(records) - len(pending_indices)} "
            f"misses={len(pending_indices)} workers={MAX_WORKERS}"
        )

    def work(index: int) -> tuple[int, PredictionRecord]:
        row = records[index]
        key = keys[index]
        scorer = scorer_factory()
        prediction = _score_one_with_retry(scorer, row, question)
        prediction.template_version = template_version
        with cache_lock:
            cache.put(key, prediction)
        return index, prediction

    if pending_indices:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(work, idx): idx for idx in pending_indices}
            done = 0
            for future in as_completed(futures):
                index, prediction = future.result()
                predictions[index] = prediction
                new_calls += 1
                new_billed += float(prediction.billed_units or 0.0)
                done += 1
                if done % 100 == 0 or done == len(pending_indices):
                    with progress_lock:
                        PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)
                        with PROGRESS_LOG.open("a", encoding="utf-8") as handle:
                            handle.write(
                                f"{run_id}\t{arm}\t{dataset}\tscored={done}\t"
                                f"pending={len(pending_indices)}\n"
                            )
                    print(f"{dataset}: progress {done}/{len(pending_indices)}")

    ordered = [p for p in predictions if p is not None]
    if len(ordered) != len(records):
        raise SystemExit(f"{dataset}: missing predictions after scoring")
    ordered.sort(key=lambda row: row.example_id)
    return ordered, new_calls, new_billed


def _score_one_with_retry(
    scorer: Any, record: ExampleRecord, question: QuestionSpec
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
            if not _is_retryable(exc):
                raise
            if attempt + 1 >= MAX_SCORE_RETRIES:
                break
            time.sleep(delay)
            delay *= 2.0
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("score failed without exception")


def _is_retryable(exc: Exception) -> bool:
    message = str(exc).lower()
    if any(marker in message for marker in RATE_LIMIT_MARKERS):
        return True
    return any(marker in message for marker in SERVER_ERROR_MARKERS)


def _read_apply_guardrail_quota() -> dict[str, Any]:
    from botocore.exceptions import ClientError

    from shared.secrets import build_boto3_session

    session = build_boto3_session()
    client = session.client("service-quotas", region_name="us-east-2")
    try:
        response = client.get_service_quota(
            ServiceCode="bedrock",
            QuotaCode="L-8B3E1399",
        )
        quota = response.get("Quota", {})
        return {"source": "service-quotas", "quota": quota}
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        return {
            "source": "service-quotas",
            "error": f"{code}: {exc}",
            "note": "quota API denied or unavailable; continuing",
        }
    except Exception as exc:  # noqa: BLE001
        return {"source": "service-quotas", "error": str(exc)}


def _price_line(arm: str, study: dict[str, Any]) -> tuple[float, str]:
    prices = study.get("prices_usd", {})
    if arm == "jev":
        return float(prices.get("jev_per_million_input_tokens", 0.042)), "per 1e6 input tokens"
    if arm == "clef":
        return float(prices.get("clef_per_million_input_tokens", 0.24)), "per 1e6 input tokens"
    if arm == "clef-flash":
        return float(prices.get("clef_flash_per_million_input_tokens", 0.038)), "per 1e6 input tokens"
    if arm == "guardrails":
        return float(prices.get("guardrails_per_1000_text_units", 0.15)), "per 1000 text units"
    return 0.0, ""


def _estimate_usd(arm: str, billed_units: float, study: dict[str, Any]) -> float:
    price, unit = _price_line(arm, study)
    if "1e6" in unit:
        return billed_units / 1_000_000 * price
    if "1000" in unit:
        return billed_units / 1000 * price
    return 0.0


def _stringify_json_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stringify_json_keys(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_stringify_json_keys(item) for item in value]
    return value


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
        if raw is not None:
            payload["raw_response"] = json.dumps(_stringify_json_keys(raw), sort_keys=True)
    frame = pd.DataFrame(rows_payload)
    parquet_path = out_dir / f"{dataset}.parquet"
    frame.to_parquet(parquet_path, index=False)
    print(f"wrote {len(predictions)} rows to {jsonl_path} and {parquet_path}")


def _write_manifest(
    run_id: str,
    *,
    arms: list[str],
    datasets: list[str],
    records_by_dataset: dict[str, list[ExampleRecord]],
    template_versions: dict[str, str],
    dataset_revisions: dict[str, str],
    billing_by_arm: dict[str, ArmBilling],
    apply_guardrail_quota: dict[str, Any] | None,
    partial: bool,
    harness: bool = False,
    threshold: float = 0.5,
) -> Path:
    study = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    models = {arm: _model_version(arm, study) for arm in arms}
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "partial": partial,
        "harness": harness,
        "arms": arms,
        "models": models,
        "guardrail_id": study.get("guardrail_id"),
        "guardrail_version": study.get("guardrail_version"),
        "region": study.get("region", "us-east-2"),
        "prices_usd": study.get("prices_usd", {}),
        "threshold": threshold,
        "dataset_revisions": dataset_revisions,
        "template_versions": template_versions,
        "apply_guardrail_quota": apply_guardrail_quota,
        "datasets": {},
        "billing": {},
    }
    for name in datasets:
        rows = len(records_by_dataset.get(name, []))
        manifest["datasets"][name] = {"rows": rows}
    for arm, stats in billing_by_arm.items():
        manifest["billing"][arm] = {
            "new_provider_calls": stats.new_provider_calls,
            "billed_units": stats.billed_units,
            "estimated_usd": _estimate_usd(arm, stats.billed_units, study),
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
