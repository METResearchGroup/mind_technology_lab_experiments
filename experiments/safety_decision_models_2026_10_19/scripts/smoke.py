"""Twenty-item smoke test per arm (step 3).

Run from the experiment folder:

    uv run python scripts/smoke.py
    uv run python scripts/smoke.py --arms jev clef clef-flash
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.cache import ResponseCache  # noqa: E402
from shared.records import (  # noqa: E402
    ExampleRecord,
    PredictionRecord,
    QuestionItem,
    QuestionSpec,
)
from scorers.clef import ClefScorer, TRUNCATED_STATUS  # noqa: E402
from scorers.guardrails import GuardrailsScorer  # noqa: E402
from scorers.jev import JevScorer, MAX_TOKENS_ERROR  # noqa: E402

TEMPLATE_DIR = EXPERIMENT_ROOT / "data" / "templates"
STUDY_CONFIG = EXPERIMENT_ROOT / "configs" / "study.json"
DEV_POOL_SIZE = 20
SMOKE_ITEM_COUNT = 20
DEFAULT_ARMS = ("jev", "clef", "clef-flash")
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
TRAIN_DEV_SPLITS = {"toxigen", "toxicchat", "prompt_injections"}
VALIDATION_DEV_SPLITS = {"go_emotions", "emotion"}
HASH_HOLDOUT_DATASETS = {
    "openai_moderation",
    "wildguardmix",
    "do_not_answer",
    "xstest",
    "harmbench",
    "jailbreakbench",
}
OPENAI_MOD_HEADS = ("S", "H", "V", "HR", "SH", "S3", "H2", "V2")
JEV_HARNESS_DATASETS = {
    "toxigen",
    "openai_moderation",
    "toxicchat",
    "prompt_injections",
    "go_emotions",
    "emotion",
}
RATE_LIMIT_MARKERS = ("rate limit", "429", "too many requests", "throttl")
MAX_SCORE_RETRIES = 6
RETRY_BASE_SECONDS = 2.0
BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE)
LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{32,}")


@dataclass
class PassStats:
    """Provider call accounting for one arm pass."""

    predictions: int = 0
    null_probabilities: int = 0
    provider_calls: int = 0
    billed_units: float = 0.0


@dataclass
class ArmRunResult:
    """Aggregated smoke outcome for one arm."""

    arm: str
    pass1: PassStats = field(default_factory=PassStats)
    pass2: PassStats = field(default_factory=PassStats)
    predictions: list[PredictionRecord] = field(default_factory=list)


def main() -> None:
    """Run smoke for requested arms."""
    args = _parse_args()
    arms = list(args.arms)
    guardrail_id = _guardrail_id()
    if not guardrail_id:
        print("guardrails: deferred to step 5 (no guardrail_id in configs/study.json)")

    smoke_rows = select_smoke_records()
    print(f"smoke: selected {len(smoke_rows)} development rows")
    for row in smoke_rows:
        print(f"  {row.dataset}\t{row.example_id}")

    if "guardrails" in arms:
        if not guardrail_id:
            arms = [arm for arm in arms if arm != "guardrails"]
        else:
            print(f"guardrails: using configured guardrail id (length {len(guardrail_id)})")

    cache = ResponseCache()
    failed = False
    results: dict[str, ArmRunResult] = {}

    for arm in arms:
        print(f"\n=== arm {arm} pass 1 ===")
        result = run_arm_pass(
            arm, smoke_rows, cache, pass_label="pass1", allow_provider_calls=True
        )
        results[arm] = result
        _print_pass_stats(arm, "pass1", result.pass1)
        if result.pass1.null_probabilities:
            failed = True
        if result.pass1.provider_calls != len(smoke_rows):
            print(
                f"warning: expected {len(smoke_rows)} provider calls on pass 1, "
                f"got {result.pass1.provider_calls}"
            )

        print(f"\n=== arm {arm} pass 2 (cache only) ===")
        pass2 = run_arm_pass(
            arm, smoke_rows, cache, pass_label="pass2", allow_provider_calls=False
        )
        result.pass2 = pass2.pass1
        _print_pass_stats(arm, "pass2", result.pass2)
        if result.pass2.provider_calls != 0:
            print(f"FAIL: pass 2 made {result.pass2.provider_calls} provider calls")
            failed = True
        if result.pass2.null_probabilities:
            failed = True

    if "jev" in results and not failed:
        print("\n=== Jev harness primary metrics (smoke subset) ===")
        try:
            print_jev_metrics(smoke_rows, results["jev"].predictions)
        except SystemExit as exc:
            print(f"FAIL: Jev metric comparability: {exc}")
            failed = True

    if failed:
        raise SystemExit(1)
    print("\nsmoke: all checks passed")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="20-item decision-model smoke test.")
    parser.add_argument(
        "--arms",
        nargs="+",
        default=list(DEFAULT_ARMS),
        choices=["jev", "clef", "clef-flash", "guardrails"],
    )
    return parser.parse_args()


def _guardrail_id() -> str:
    if not STUDY_CONFIG.is_file():
        return ""
    payload = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    return str(payload.get("guardrail_id", "")).strip()


def _model_version(arm: str) -> str:
    payload = json.loads(STUDY_CONFIG.read_text(encoding="utf-8"))
    models = payload.get("models", {})
    return str(models.get(arm, arm))


def _load_dataset_module(dataset: str):
    return importlib.import_module(DATASET_MODULES[dataset])


def _loader_split(dataset: str) -> str | None:
    if dataset in TRAIN_DEV_SPLITS:
        return "train"
    if dataset in VALIDATION_DEV_SPLITS:
        return "validation"
    return None


def _is_holdout_example(example_id: str) -> bool:
    digest = hashlib.sha256(example_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % 100 < 20


def load_dev_pool(dataset: str, limit: int = DEV_POOL_SIZE) -> list[ExampleRecord]:
    """Stable development pool per step 2 (first ``limit`` rows by example_id)."""
    module = _load_dataset_module(dataset)
    split = _loader_split(dataset)
    if split is not None:
        records = module.load_records(split)
        records.sort(key=lambda row: row.example_id)
        return records[:limit]
    records = module.load_records()
    holdout = [row for row in records if _is_holdout_example(row.example_id)]
    holdout.sort(key=lambda row: row.example_id)
    return holdout[:limit]


def select_smoke_records() -> list[ExampleRecord]:
    """Round-robin the first rows of each dataset dev pool until 20 items."""
    pools: dict[str, list[ExampleRecord]] = {}
    for name in DATASET_ORDER:
        pool = load_dev_pool(name, limit=DEV_POOL_SIZE)
        if not pool:
            raise SystemExit(f"empty development pool for dataset {name}")
        pools[name] = pool

    selected: list[ExampleRecord] = []
    index = 0
    while len(selected) < SMOKE_ITEM_COUNT:
        progressed = False
        for name in DATASET_ORDER:
            pool = pools[name]
            if index < len(pool):
                selected.append(pool[index])
                progressed = True
                if len(selected) >= SMOKE_ITEM_COUNT:
                    break
        if not progressed:
            raise SystemExit("could not fill 20 smoke rows from development pools")
        index += 1
    return selected


def load_question(dataset: str) -> tuple[QuestionSpec, str]:
    """Load QuestionSpec and file-byte template hash."""
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


def _build_scorer(arm: str):
    if arm == "jev":
        return JevScorer()
    if arm in ("clef", "clef-flash"):
        return ClefScorer(arm=arm)
    return GuardrailsScorer()


def run_arm_pass(
    arm: str,
    records: list[ExampleRecord],
    cache: ResponseCache,
    *,
    pass_label: str,
    allow_provider_calls: bool,
) -> ArmRunResult:
    """Score all rows for one arm; pass 2 must not call providers."""
    scorer = _build_scorer(arm)
    model_version = _model_version(arm)
    by_dataset: dict[str, list[ExampleRecord]] = defaultdict(list)
    for record in records:
        by_dataset[record.dataset].append(record)

    predictions: list[PredictionRecord] = []
    stats = PassStats()

    for dataset, group in sorted(by_dataset.items()):
        question, template_version = load_question(dataset)
        misses: list[ExampleRecord] = []
        miss_keys: list[str] = []
        for record in group:
            key = ResponseCache.cache_key(
                arm, model_version, template_version, record.example_id
            )
            cached = cache.get(key)
            if cached is not None:
                predictions.append(cached)
                stats.predictions += 1
                if cached.probability is None and arm != "guardrails":
                    stats.null_probabilities += 1
                    _report_null_prediction(arm, cached)
                continue
            misses.append(record)
            miss_keys.append(key)

        if not misses:
            continue
        if not allow_provider_calls:
            stats.provider_calls += len(misses)
            for record in misses:
                stats.predictions += 1
                stats.null_probabilities += 1
                print(
                    f"FAIL: cache miss on {pass_label} for {arm} "
                    f"{record.example_id}"
                )
            continue

        scored = _score_with_retry(scorer, misses, question)
        stats.provider_calls += len(misses)
        if len(scored) != len(misses):
            raise SystemExit(
                f"scorer returned {len(scored)} rows for {len(misses)} inputs ({arm})"
            )
        for key, prediction in zip(miss_keys, scored, strict=True):
            prediction.template_version = template_version
            cache.put(key, prediction)
            predictions.append(prediction)
            stats.predictions += 1
            stats.billed_units += float(prediction.billed_units or 0.0)
            if prediction.probability is None and arm != "guardrails":
                stats.null_probabilities += 1
                _report_null_prediction(arm, prediction)

    predictions.sort(key=lambda row: row.example_id)
    return ArmRunResult(arm=arm, pass1=stats, predictions=predictions)


def _score_with_retry(
    scorer: Any, records: list[ExampleRecord], question: QuestionSpec
) -> list[PredictionRecord]:
    delay = RETRY_BASE_SECONDS
    last_exc: Exception | None = None
    for attempt in range(MAX_SCORE_RETRIES):
        try:
            return scorer.score(records, question)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            message = str(exc).lower()
            if not any(marker in message for marker in RATE_LIMIT_MARKERS):
                raise
            if attempt + 1 >= MAX_SCORE_RETRIES:
                break
            print(
                f"rate limited; retry {attempt + 1}/{MAX_SCORE_RETRIES} "
                f"after {delay:.1f}s"
            )
            time.sleep(delay)
            delay *= 2.0
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("score failed without exception")


def _report_null_prediction(arm: str, prediction: PredictionRecord) -> None:
    status = prediction.error_status or "(none)"
    raw = _redact_error(json.dumps(prediction.raw_response, default=str))
    print(
        f"FAIL: {arm} {prediction.example_id} missing probability; "
        f"error_status={status}; raw={raw[:240]}"
    )
    if prediction.error_status not in (
        None,
        TRUNCATED_STATUS,
        MAX_TOKENS_ERROR,
    ):
        print(
            "note: probability missing with non-truncation error_status "
            f"({status})"
        )


def _redact_error(text: str) -> str:
    redacted = BEARER_RE.sub("Bearer [REDACTED]", text)
    redacted = LONG_TOKEN_RE.sub("[REDACTED]", redacted)
    if len(redacted) > 400:
        redacted = redacted[:400] + "..."
    return redacted


def _print_pass_stats(arm: str, label: str, stats: PassStats) -> None:
    print(
        f"{arm} {label}: predictions={stats.predictions} "
        f"null_probabilities={stats.null_probabilities} "
        f"provider_calls={stats.provider_calls} "
        f"billed_units={stats.billed_units:.1f}"
    )


def print_jev_metrics(
    records: list[ExampleRecord],
    predictions: list[PredictionRecord],
) -> None:
    """Print harness primary metrics for overlapping datasets in the smoke set."""
    by_id = {row.example_id: row for row in records}
    pred_by_id = {row.example_id: row for row in predictions}
    by_dataset: dict[str, list[ExampleRecord]] = defaultdict(list)
    for record in records:
        if record.dataset in JEV_HARNESS_DATASETS:
            by_dataset[record.dataset].append(record)

    for dataset in sorted(by_dataset):
        rows = by_dataset[dataset]
        preds = [pred_by_id[row.example_id] for row in rows]
        if dataset == "toxigen":
            _metric_toxigen(rows, preds)
        elif dataset == "openai_moderation":
            _metric_openai_moderation(rows, preds)
        elif dataset == "toxicchat":
            _metric_toxicchat(rows, preds)
        elif dataset == "prompt_injections":
            _metric_prompt_injections(rows, preds)
        elif dataset == "go_emotions":
            _metric_go_emotions(rows, preds)
        elif dataset == "emotion":
            _metric_emotion(rows, preds)


def _answers_map(prediction: PredictionRecord) -> dict[str, dict[str, Any]]:
    raw = prediction.raw_response or {}
    answers = raw.get("answers", {})
    if not isinstance(answers, dict):
        return {}
    return {str(key): _normalize_answer(value) for key, value in answers.items()}


def _normalize_answer(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _noul_value(answer: dict[str, Any]) -> float | None:
    if answer.get("type") == "noul" or "noul" in answer:
        noul = answer.get("noul")
        return float(noul) if noul is not None else None
    return None


def _choice_value(answer: dict[str, Any]) -> str | None:
    choice = answer.get("choice")
    if choice is None:
        return None
    return str(choice)


def _metric_toxigen(
    rows: list[ExampleRecord], preds: list[PredictionRecord]
) -> None:
    golds: list[bool] = []
    answers: list[dict[str, Any]] = []
    for row, pred in zip(rows, preds, strict=True):
        if not isinstance(row.gold_labels, dict) or "toxic" not in row.gold_labels:
            raise SystemExit("toxigen gold_labels missing toxic")
        ans = _answers_map(pred).get("toxic")
        if ans is None or _noul_value(ans) is None:
            raise SystemExit("toxigen prediction missing toxic noul head")
        golds.append(bool(row.gold_labels["toxic"]))
        answers.append({"noul": _noul_value(ans)})
    value = _binary_accuracy(golds, answers, threshold=0.5)
    print(f"jev_metric toxigen accuracy n={len(rows)} value={value:.4f}")


def _metric_openai_moderation(
    rows: list[ExampleRecord], preds: list[PredictionRecord]
) -> None:
    for head in OPENAI_MOD_HEADS:
        ans = _answers_map(preds[0]).get(head) if preds else None
        if ans is None:
            raise SystemExit(f"openai_moderation missing answer head {head}")
    if len(rows) < 2:
        print(
            f"jev_metric openai_moderation mean_auprc n={len(rows)} "
            "value=undefined (n<2 for AUPRC on smoke sample; heads aligned)"
        )
        return
    auprcs: list[float] = []
    for head in OPENAI_MOD_HEADS:
        golds: list[bool] = []
        scores: list[float] = []
        for row, pred in zip(rows, preds, strict=True):
            if not isinstance(row.gold_labels, dict):
                raise SystemExit("openai_moderation gold_labels not a dict")
            golds.append(bool(row.gold_labels.get(head, False)))
            ans = _answers_map(pred).get(head)
            if ans is None or _noul_value(ans) is None:
                raise SystemExit(f"openai_moderation missing noul for head {head}")
            scores.append(float(_noul_value(ans)))
        auprcs.append(_average_precision(golds, scores))
    mean_auprc = sum(auprcs) / len(auprcs)
    print(
        f"jev_metric openai_moderation mean_auprc n={len(rows)} "
        f"value={mean_auprc:.4f}"
    )


def _metric_toxicchat(
    rows: list[ExampleRecord], preds: list[PredictionRecord]
) -> None:
    for head in ("toxic", "jailbreak"):
        golds: list[bool] = []
        answers: list[dict[str, Any]] = []
        for row, pred in zip(rows, preds, strict=True):
            if not isinstance(row.gold_labels, dict) or head not in row.gold_labels:
                raise SystemExit(f"toxicchat gold_labels missing {head}")
            ans = _answers_map(pred).get(head)
            if ans is None or _noul_value(ans) is None:
                raise SystemExit(f"toxicchat missing noul head {head}")
            golds.append(bool(row.gold_labels[head]))
            answers.append({"noul": _noul_value(ans)})
        value = _binary_f1(golds, answers, threshold=0.5)
        print(f"jev_metric toxicchat {head}_f1 n={len(rows)} value={value:.4f}")


def _metric_prompt_injections(
    rows: list[ExampleRecord], preds: list[PredictionRecord]
) -> None:
    golds: list[bool] = []
    answers: list[dict[str, Any]] = []
    for row, pred in zip(rows, preds, strict=True):
        if not isinstance(row.gold_labels, dict) or "answer" not in row.gold_labels:
            raise SystemExit("prompt_injections gold_labels missing answer")
        ans = _answers_map(pred).get("answer")
        if ans is None or _noul_value(ans) is None:
            raise SystemExit("prompt_injections missing answer noul head")
        golds.append(bool(row.gold_labels["answer"]))
        answers.append({"noul": _noul_value(ans)})
    value = _binary_accuracy(golds, answers, threshold=0.5)
    print(f"jev_metric prompt_injections accuracy n={len(rows)} value={value:.4f}")


def _metric_go_emotions(
    rows: list[ExampleRecord], preds: list[PredictionRecord]
) -> None:
    template_path = TEMPLATE_DIR / "go_emotions.json"
    label_names = sorted(json.loads(template_path.read_text(encoding="utf-8")).keys())
    if not label_names:
        raise SystemExit("go_emotions: empty template")
    for pred in preds:
        answers = _answers_map(pred)
        for label in label_names:
            if label not in answers or _noul_value(answers[label]) is None:
                raise SystemExit(f"go_emotions missing noul head {label}")
    gold_matrix: list[list[int]] = []
    prob_matrix: list[list[float]] = []
    for row, pred in zip(rows, preds, strict=True):
        if not isinstance(row.gold_labels, dict):
            raise SystemExit("go_emotions gold_labels not a dict")
        answers = _answers_map(pred)
        gold_matrix.append(
            [1 if row.gold_labels.get(label, False) else 0 for label in label_names]
        )
        prob_matrix.append(
            [float(_noul_value(answers[label]) or 0.0) for label in label_names]
        )
    value = _macro_f1_multilabel(gold_matrix, prob_matrix, threshold=0.5)
    print(f"jev_metric go_emotions macro_f1 n={len(rows)} value={value:.4f}")


def _metric_emotion(
    rows: list[ExampleRecord], preds: list[PredictionRecord]
) -> None:
    correct = 0
    for row, pred in zip(rows, preds, strict=True):
        if not isinstance(row.gold_labels, str):
            raise SystemExit("emotion gold_labels must be label string")
        ans = _answers_map(pred).get("answer")
        if ans is None or _choice_value(ans) is None:
            raise SystemExit("emotion missing choice answer head")
        if _choice_value(ans) == row.gold_labels:
            correct += 1
    value = correct / len(rows) if rows else math.nan
    print(f"jev_metric emotion accuracy n={len(rows)} value={value:.4f}")


def _binary_accuracy(
    golds: list[bool], answers: list[dict[str, Any]], threshold: float
) -> float:
    hits = 0
    for gold, answer in zip(golds, answers, strict=True):
        prob = float(answer["noul"])
        pred = prob >= threshold
        if pred == gold:
            hits += 1
    return hits / len(golds)


def _binary_f1(
    golds: list[bool], answers: list[dict[str, Any]], threshold: float
) -> float:
    tp = fp = fn = 0
    for gold, answer in zip(golds, answers, strict=True):
        prob = float(answer["noul"])
        pred = prob >= threshold
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif not pred and gold:
            fn += 1
    denom = 2 * tp + fp + fn
    return (2 * tp / denom) if denom else 0.0


def _macro_f1_multilabel(
    gold_matrix: list[list[int]],
    prob_matrix: list[list[float]],
    threshold: float,
) -> float:
    if not gold_matrix:
        return math.nan
    n_labels = len(gold_matrix[0])
    f1s: list[float] = []
    for j in range(n_labels):
        tp = fp = fn = 0
        for gold_row, prob_row in zip(gold_matrix, prob_matrix, strict=True):
            gold = gold_row[j] == 1
            pred = prob_row[j] >= threshold
            if pred and gold:
                tp += 1
            elif pred and not gold:
                fp += 1
            elif not pred and gold:
                fn += 1
        denom = 2 * tp + fp + fn
        f1s.append((2 * tp / denom) if denom else 0.0)
    return sum(f1s) / len(f1s)


def _average_precision(golds: list[bool], scores: list[float]) -> float:
    if not golds:
        return math.nan
    positives = sum(1 for g in golds if g)
    if positives == 0:
        return 0.0
    ordered = sorted(
        zip(scores, golds), key=lambda pair: pair[0], reverse=True
    )
    tp = 0
    precisions: list[float] = []
    for rank, (_, gold) in enumerate(ordered, start=1):
        if gold:
            tp += 1
            precisions.append(tp / rank)
    return sum(precisions) / positives if precisions else 0.0


if __name__ == "__main__":
    main()
