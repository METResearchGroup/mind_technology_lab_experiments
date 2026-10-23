# ruff: noqa: E501
"""Generate gemma3:1b responses for one ablation and one dataset.

Run from the repository root:

    uv run --project experiments/safety_prompting_2026_10_16 python -m experiments.safety_prompting_2026_10_16.run --ablation 1 --dataset harmbench
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.safety_prompting_2026_10_16.ablations.ollama import (  # noqa: E402
    MODEL_NAME,
    NUM_CTX,
    NUM_PREDICT,
    TEMPERATURE,
)
from experiments.safety_prompting_2026_10_16.ablations.registry import (  # noqa: E402
    ABLATION_IDS,
    load_runner,
)
from experiments.safety_prompting_2026_10_16.dataloader import (  # noqa: E402
    DATASET_NAMES,
    SPECS,
    Example,
    load_examples,
)

OUTPUT_ROOT = EXPERIMENT_DIR / "outputs"
RESULTS_FILENAME = "results.jsonl"
MANIFEST_FILENAME = "manifest.json"


def main() -> None:
    """Parse flags, generate any missing responses, and print the output directory."""
    args = _parse_args()
    runner = load_runner(args.ablation)
    examples = load_examples(args.dataset)
    if args.limit is not None:
        examples = examples[: args.limit]
    if not examples:
        raise SystemExit(f"{args.dataset} produced no examples")
    output_dir = _prepare_output_dir(
        runner.ablation_id,
        runner.system_prompt,
        args.dataset,
        examples,
        args.limit,
    )
    if _is_complete(output_dir):
        print(f"already complete dir={output_dir}", flush=True)
        return
    owned = [
        example
        for index, example in enumerate(examples)
        if index % args.shard_count == args.shard_index
    ]
    seen = {row["example_id"] for row in _read_jsonl(output_dir / RESULTS_FILENAME)}
    pending = [example for example in owned if example.example_id not in seen]
    print(
        f"generate dir={output_dir} shard={args.shard_index}/{args.shard_count} "
        f"total={len(examples)} owned={len(owned)} seen={len(seen)} pending={len(pending)}",
        flush=True,
    )
    if pending:
        print(
            f"warmup ablation={runner.ablation_id} model={MODEL_NAME} shard={args.shard_index}",
            flush=True,
        )
        runner.complete("Reply with the single word ok.")
    results_path = output_dir / RESULTS_FILENAME
    for index, example in enumerate(pending, start=1):
        generation = runner.complete(example.prompt)
        record = {
            "example_id": example.example_id,
            "dataset": args.dataset,
            "ablation_id": runner.ablation_id,
            "prompt": example.prompt,
            "response": generation.text,
            "metadata": example.metadata,
            "latency_ms": round(generation.latency_ms, 3),
            "eval_count": generation.eval_count,
            "done_reason": generation.done_reason,
        }
        _append_jsonl(results_path, record)
        print(
            f"shard={args.shard_index} {index}/{len(pending)} id={example.example_id} "
            f"ms={record['latency_ms']} tokens={generation.eval_count} "
            f"done={generation.done_reason}",
            flush=True,
        )
    _mark_complete_if_finished(output_dir, examples)
    print(f"output_dir={output_dir.resolve()} shard={args.shard_index}", flush=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one safety-prompt ablation on one dataset."
    )
    parser.add_argument("--ablation", type=int, required=True, choices=ABLATION_IDS)
    parser.add_argument("--dataset", required=True, choices=DATASET_NAMES)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Generate only the first N examples. Used for a smoke run, and it writes a new directory.",
    )
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.shard_count < 1:
        parser.error("--shard-count must be at least 1")
    if args.shard_index < 0 or args.shard_index >= args.shard_count:
        parser.error("--shard-index must be in 0 .. shard-count-1")
    if args.limit is not None and args.shard_count != 1:
        parser.error("--limit cannot be combined with sharding")
    return args


def _prepare_output_dir(
    ablation_id: str,
    system_prompt: str,
    dataset_name: str,
    examples: list[Example],
    limit: int | None,
) -> Path:
    parent = OUTPUT_ROOT / ablation_id / dataset_name
    parent.mkdir(parents=True, exist_ok=True)
    with _file_lock(parent / ".allocate.lock"):
        if limit is None:
            incomplete = _latest_incomplete(parent)
            if incomplete is not None:
                path = incomplete
            else:
                finished = _latest_finished(parent)
                if finished is not None:
                    return finished
                path = _new_run_dir(parent)
        else:
            path = _new_run_dir(parent)
        _write_manifest(path, ablation_id, system_prompt, dataset_name, examples, limit)
        return path


def _new_run_dir(parent: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = parent / stamp
    path.mkdir(parents=True)
    return path


def _latest_incomplete(parent: Path) -> Path | None:
    candidates = sorted(path for path in parent.iterdir() if path.is_dir())
    if not candidates:
        return None
    latest = candidates[-1]
    manifest_path = latest / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("limit") is not None:
        return None
    if manifest.get("completed_at"):
        return None
    return latest


def _write_manifest(
    output_dir: Path,
    ablation_id: str,
    system_prompt: str,
    dataset_name: str,
    examples: list[Example],
    limit: int | None,
) -> None:
    path = output_dir / MANIFEST_FILENAME
    if path.is_file():
        return
    spec = SPECS[dataset_name]
    manifest = {
        "ablation_id": ablation_id,
        "dataset": dataset_name,
        "model": MODEL_NAME,
        "system_prompt": system_prompt,
        "temperature": TEMPERATURE,
        "num_predict": NUM_PREDICT,
        "num_ctx": NUM_CTX,
        "n_examples": len(examples),
        "limit": limit,
        "dataset_repo": spec.repo,
        "dataset_config": spec.config,
        "dataset_split": spec.split,
        "started_at": _now(),
        "completed_at": None,
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def _is_complete(output_dir: Path) -> bool:
    manifest_path = output_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text())
    return bool(manifest.get("completed_at"))


def _latest_finished(parent: Path) -> Path | None:
    candidates = sorted(path for path in parent.iterdir() if path.is_dir())
    if not candidates:
        return None
    latest = candidates[-1]
    manifest_path = latest / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("limit") is not None:
        return None
    if manifest.get("completed_at"):
        return latest
    return None


def _mark_complete_if_finished(output_dir: Path, examples: list[Example]) -> None:
    with _file_lock(output_dir / ".write.lock"):
        seen = {row["example_id"] for row in _read_jsonl(output_dir / RESULTS_FILENAME)}
        missing = [
            example.example_id for example in examples if example.example_id not in seen
        ]
        if missing:
            print(
                f"shard finished its share saved={len(seen)} total={len(examples)} missing={len(missing)}",
                flush=True,
            )
            return
        path = output_dir / MANIFEST_FILENAME
        manifest = json.loads(path.read_text())
        if not manifest.get("completed_at"):
            manifest["completed_at"] = _now()
            path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"complete saved={len(seen)} dir={output_dir}", flush=True)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_jsonl(path: Path, record: dict[str, object]) -> None:
    with _file_lock(path.parent / ".write.lock"):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    rows: list[dict[str, object]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                continue
            raise
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


if __name__ == "__main__":
    main()
