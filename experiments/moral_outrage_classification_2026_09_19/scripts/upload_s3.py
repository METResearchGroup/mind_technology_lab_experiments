"""Upload the experiment tree to the lab S3 prefix.

Run from the experiment folder:

    uv run python scripts/upload_s3.py
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.aws_region import AWS_REGION
from shared.secrets import build_boto3_session

BUCKET = "mind-technology-lab-experiments"
PREFIX = "experiments/moral_outrage_classification_2026_09_19/"
SKIP_DIR_NAMES = {".venv", "__pycache__", ".pytest_cache", ".git"}
SKIP_FILE_NAMES = {
    "26k_training_data.csv",
    "perspective_api_labeled_26k_twitter_dataset.csv",
    ".env",
}
UPLOAD_COMPLETE_LINE = (
    "UPLOAD COMPLETE s3://mind-technology-lab-experiments/"
    "experiments/moral_outrage_classification_2026_09_19/"
)


def s3_key_for_local_path(local_path: Path, experiment_root: Path) -> str:
    """Map a local file to the experiment S3 key."""
    relative = local_path.resolve().relative_to(experiment_root.resolve())
    return PREFIX + relative.as_posix()


def iter_upload_paths(experiment_root: Path) -> list[Path]:
    """List files to upload, excluding venv, pycache, and the full CSV."""
    paths: list[Path] = []
    for path in experiment_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.name in SKIP_FILE_NAMES:
            continue
        paths.append(path)
    return paths


def upload_tree(
    experiment_root: Path,
    put_object: Callable[..., object],
) -> list[str]:
    """Upload allowed local files. Returns uploaded keys."""
    keys: list[str] = []
    for path in iter_upload_paths(experiment_root):
        key = s3_key_for_local_path(path, experiment_root)
        put_object(Bucket=BUCKET, Key=key, Body=path.read_bytes())
        keys.append(key)
    return keys


def main() -> None:
    session = build_boto3_session()
    client = session.client("s3", region_name=AWS_REGION)
    upload_tree(EXPERIMENT_ROOT, client.put_object)
    print(UPLOAD_COMPLETE_LINE)


if __name__ == "__main__":
    main()
