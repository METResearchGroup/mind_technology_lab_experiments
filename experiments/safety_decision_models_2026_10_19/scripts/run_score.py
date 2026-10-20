"""Score a dataset split with one arm, using the response cache.

Run from the experiment folder:

    uv run python scripts/run_score.py --dataset toxigen --arm jev --split test
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.cache import ResponseCache  # noqa: E402
from shared.records import QuestionItem, QuestionSpec  # noqa: E402
from scorers.clef import ClefScorer  # noqa: E402
from scorers.guardrails import GuardrailsScorer  # noqa: E402
from scorers.jev import JevScorer  # noqa: E402

TEMPLATE_DIR = EXPERIMENT_ROOT / "data" / "templates"
DATASET_MODULES = {
    "toxigen": "datasets.toxigen",
    "openai_moderation": "datasets.openai_moderation",
    "toxicchat": "datasets.toxicchat",
    "prompt_injections": "datasets.prompt_injections",
    "wildguardmix": "datasets.wildguardmix",
    "do_not_answer": "datasets.do_not_answer",
    "xstest": "datasets.xstest",
    "harmbench": "datasets.harmbench",
    "jailbreakbench": "datasets.jailbreakbench",
    "go_emotions": "datasets.go_emotions",
    "emotion": "datasets.emotion",
}


def main() -> None:
    """Load records, score with cache, and write prediction JSONL."""
    args = _parse_args()
    records = _load_records(args.dataset, args.split)
    question = _load_question(args.dataset)
    template_version = _template_hash(question)
    scorer = _build_scorer(args.arm)
    cache = ResponseCache()
    predictions = []
    for record in records:
        key = ResponseCache.cache_key(
            args.arm, _model_version(args.arm), template_version, record.example_id
        )
        cached = cache.get(key)
        if cached is not None:
            predictions.append(cached)
            continue
        batch = scorer.score([record], question)
        if not batch:
            continue
        prediction = batch[0]
        prediction.template_version = template_version
        cache.put(key, prediction)
        predictions.append(prediction)
    out_dir = EXPERIMENT_ROOT / "outputs" / "predictions" / args.run_id / args.arm
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.dataset}.jsonl"
    with out_path.open("w", encoding="utf-8") as handle:
        for row in predictions:
            handle.write(row.model_dump_json())
            handle.write("\n")
    print(f"wrote {len(predictions)} rows to {out_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score one dataset with one arm.")
    parser.add_argument("--dataset", required=True, choices=sorted(DATASET_MODULES))
    parser.add_argument("--arm", required=True, choices=["jev", "clef", "clef-flash", "guardrails"])
    parser.add_argument("--split", default="test")
    parser.add_argument("--run-id", default="local")
    return parser.parse_args()


def _load_records(dataset: str, split: str) -> list:
    module_name = DATASET_MODULES[dataset]
    module = importlib.import_module(module_name)
    return module.load_records(split)


def _load_question(dataset: str) -> QuestionSpec:
    path = TEMPLATE_DIR / f"{dataset}.json"
    if not path.is_file():
        return QuestionSpec(
            questions={
                "default": QuestionItem(
                    type="noul",
                    instructions="Is `text` harmful?",
                    criteria=None,
                )
            }
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return QuestionSpec.model_validate(payload)


def _template_hash(question: QuestionSpec) -> str:
    digest = hashlib.sha256(question.model_dump_json().encode("utf-8")).hexdigest()
    return digest[:16]


def _build_scorer(arm: str):
    if arm == "jev":
        return JevScorer()
    if arm in ("clef", "clef-flash"):
        return ClefScorer(arm=arm)
    return GuardrailsScorer()


def _model_version(arm: str) -> str:
    study_path = EXPERIMENT_ROOT / "configs" / "study.json"
    payload = json.loads(study_path.read_text(encoding="utf-8"))
    models = payload.get("models", {})
    return str(models.get(arm, arm))


if __name__ == "__main__":
    main()
