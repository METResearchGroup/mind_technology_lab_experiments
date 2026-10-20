"""Upload artifacts to the lab S3 prefix (skips Do-Not-Answer question text)."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.secrets import AWS_REGION, build_boto3_session

BUCKET = "mind-technology-lab-experiments"
PREFIX = "experiments/safety_decision_models_2026_10_19/"
SKIP_DIR_NAMES = {".venv", "__pycache__", ".pytest_cache", ".git"}
SKIP_FILE_NAMES = {".env"}
UPLOAD_COMPLETE_LINE = (
    "UPLOAD COMPLETE s3://mind-technology-lab-experiments/"
    "experiments/safety_decision_models_2026_10_19/"
)

DNA_SNAPSHOT_PREFIX = EXPERIMENT_ROOT / "data" / "snapshots" / "do_not_answer"
DNA_RECORDS = EXPERIMENT_ROOT / "data" / "records" / "do_not_answer.parquet"
CACHE_DB = EXPERIMENT_ROOT / "cache" / "responses.db"


def s3_key_for_local_path(local_path: Path, experiment_root: Path) -> str:
    relative = local_path.resolve().relative_to(experiment_root.resolve())
    return PREFIX + relative.as_posix()


def _path_contains_dna_question_text(path: Path) -> bool:
    if DNA_SNAPSHOT_PREFIX in path.parents or path == DNA_RECORDS:
        return True
    if path.suffix == ".parquet" and "do_not_answer" in path.name:
        try:
            import pandas as pd

            frame = pd.read_parquet(path, columns=["example_id"])
            if len(frame) == 0:
                return False
            # Heuristic: prediction files with raw_response may embed question text
            full = pd.read_parquet(path)
            if "text" in full.columns:
                return True
            if "raw_response" in full.columns:
                sample = str(full.iloc[0]["raw_response"])
                return "question" in sample.lower() and len(sample) > 200
        except Exception:
            return True
    if path.suffix == ".jsonl" and "do_not_answer" in path.name:
        line = path.read_text(encoding="utf-8").splitlines()[:1]
        if line and len(line[0]) > 500:
            return True
    return False


def _cache_payload_has_dna_text(payload: str) -> bool:
    lowered = payload.lower()
    if "do_not_answer" not in lowered and "do-not-answer" not in lowered:
        return False
    return "question" in lowered or '"text"' in lowered


def iter_upload_paths(experiment_root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in experiment_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.name in SKIP_FILE_NAMES:
            continue
        rel = path.relative_to(experiment_root)
        if rel.parts[:3] == ("data", "snapshots", "do_not_answer"):
            continue
        if rel == Path("data/records/do_not_answer.parquet"):
            continue
        if _path_contains_dna_question_text(path):
            continue
        paths.append(path)
    return paths


def upload_tree(
    experiment_root: Path,
    put_object: Callable[..., object],
) -> list[str]:
    keys: list[str] = []
    for path in iter_upload_paths(experiment_root):
        key = s3_key_for_local_path(path, experiment_root)
        put_object(Bucket=BUCKET, Key=key, Body=path.read_bytes())
        keys.append(key)

    if CACHE_DB.is_file():
        conn = sqlite3.connect(CACHE_DB)
        try:
            rows = conn.execute("SELECT cache_key, payload FROM responses").fetchall()
        finally:
            conn.close()
        sanitized: list[tuple[str, str]] = []
        for cache_key, payload in rows:
            if _cache_payload_has_dna_text(payload):
                continue
            sanitized.append((cache_key, payload))
        if sanitized:
            import tempfile

            tmp = Path(tempfile.mkdtemp()) / "responses_sanitized.db"
            conn = sqlite3.connect(tmp)
            conn.execute(
                "CREATE TABLE responses (cache_key TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            conn.executemany(
                "INSERT INTO responses(cache_key, payload) VALUES (?, ?)", sanitized
            )
            conn.commit()
            conn.close()
            key = PREFIX + "cache/responses.db"
            put_object(Bucket=BUCKET, Key=key, Body=tmp.read_bytes())
            keys.append(key)
    return keys


def main() -> None:
    session = build_boto3_session()
    client = session.client("s3", region_name=AWS_REGION)
    upload_tree(EXPERIMENT_ROOT, client.put_object)
    print(UPLOAD_COMPLETE_LINE)


if __name__ == "__main__":
    main()
