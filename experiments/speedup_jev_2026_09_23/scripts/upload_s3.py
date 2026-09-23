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

BUCKET = "mind-technology-lab-experiments"
PREFIX = "experiments/speedup_jev_2026_09_23/"
SKIP_DIR_NAMES = {".venv", "__pycache__", ".pytest_cache", ".git"}
SKIP_FILE_NAMES = {".env"}
UPLOAD_COMPLETE_LINE = (
    "UPLOAD COMPLETE s3://mind-technology-lab-experiments/"
    "experiments/speedup_jev_2026_09_23/"
)


def s3_key_for_local_path(local_path: Path, experiment_root: Path) -> str:
    """Map a local file to the experiment S3 key."""
    raise NotImplementedError


def iter_upload_paths(experiment_root: Path) -> list[Path]:
    """List files to upload, excluding venv, pycache, and env files."""
    raise NotImplementedError


def upload_tree(
    experiment_root: Path,
    put_object: Callable[..., object],
) -> list[str]:
    """Upload allowed local files. Returns uploaded keys."""
    raise NotImplementedError


def main() -> None:
    """Upload the experiment folder to S3."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
