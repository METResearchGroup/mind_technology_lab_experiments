"""Download the PR 20 sample from S3 and validate the manifest.

Run from the experiment folder:

    uv run python -c "from shared.data import download_inputs; download_inputs()"
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from shared.aws_region import AWS_REGION
from shared.secrets import build_boto3_session

SOURCE_BUCKET = "mind-technology-lab-experiments"
SOURCE_PREFIX = "experiments/moral_outrage_classification_2026_09_19/"
SAMPLE_S3_KEY = SOURCE_PREFIX + "data/sample_1000.parquet"
MANIFEST_S3_KEY = SOURCE_PREFIX + "data/sample_1000.manifest.json"
PR20_LABELS_S3_KEY = SOURCE_PREFIX + "outputs/jev/labels.parquet"
PR20_RESULTS_S3_KEY = SOURCE_PREFIX + "outputs/jev/results.json"
SAMPLE_PARQUET_NAME = "sample_1000.parquet"
SAMPLE_MANIFEST_NAME = "sample_1000.manifest.json"
PR20_JEV_LABELS_NAME = "pr20_jev_labels.parquet"
PR20_JEV_RESULTS_NAME = "pr20_jev_results.json"
SAMPLE_SEED = 20260919
SAMPLE_ROW_COUNT = 1000
SAMPLE_GOLD_0_COUNT = 560
SAMPLE_GOLD_1_COUNT = 440
ROW_ID_FIELD = "source_row_id"
GOLD_LABEL_COLUMN = "gold_label"
MANIFEST_SEED_KEY = "seed"
MANIFEST_ROW_COUNT_KEY = "n_rows"
MANIFEST_GOLD_0_KEY = "n_gold_0"
MANIFEST_GOLD_1_KEY = "n_gold_1"
MANIFEST_ROW_ID_FIELD_KEY = "row_id_field"

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = EXPERIMENT_ROOT / "data"


@dataclass(frozen=True)
class RemoteInputFile:
    """One PR 20 artifact to copy from S3 into ``data/``."""

    s3_key: str
    local_name: str


REMOTE_INPUT_FILES: tuple[RemoteInputFile, ...] = (
    RemoteInputFile(SAMPLE_S3_KEY, SAMPLE_PARQUET_NAME),
    RemoteInputFile(MANIFEST_S3_KEY, SAMPLE_MANIFEST_NAME),
    RemoteInputFile(PR20_LABELS_S3_KEY, PR20_JEV_LABELS_NAME),
    RemoteInputFile(PR20_RESULTS_S3_KEY, PR20_JEV_RESULTS_NAME),
)


def _s3_client() -> object:
    session = build_boto3_session()
    return session.client("s3", region_name=AWS_REGION)


def _local_path(local_name: str) -> Path:
    return DATA_DIR / local_name


def _download_if_missing(client: object, remote_file: RemoteInputFile) -> None:
    local_path = _local_path(remote_file.local_name)
    if local_path.is_file():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    client.download_file(SOURCE_BUCKET, remote_file.s3_key, str(local_path))


def download_inputs() -> None:
    """Download each PR 20 input file that is not already on disk."""
    client = _s3_client()
    for remote_file in REMOTE_INPUT_FILES:
        _download_if_missing(client, remote_file)


def _validate_manifest_field(
    manifest: dict[str, object], key: str, expected: object, label: str
) -> None:
    actual = manifest.get(key)
    if actual != expected:
        raise ValueError(f"manifest {label} {actual!r} != {expected!r}")


def validate_manifest(manifest: dict[str, object]) -> None:
    """Raise ``ValueError`` when manifest fields differ from locked constants."""
    _validate_manifest_field(manifest, MANIFEST_SEED_KEY, SAMPLE_SEED, "seed")
    _validate_manifest_field(
        manifest, MANIFEST_ROW_COUNT_KEY, SAMPLE_ROW_COUNT, "n_rows"
    )
    _validate_manifest_field(
        manifest, MANIFEST_GOLD_0_KEY, SAMPLE_GOLD_0_COUNT, "n_gold_0"
    )
    _validate_manifest_field(
        manifest, MANIFEST_GOLD_1_KEY, SAMPLE_GOLD_1_COUNT, "n_gold_1"
    )
    _validate_manifest_field(
        manifest, MANIFEST_ROW_ID_FIELD_KEY, ROW_ID_FIELD, "row_id_field"
    )


def _read_manifest() -> dict[str, object]:
    manifest_path = _local_path(SAMPLE_MANIFEST_NAME)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be a mapping")
    return payload


def _validate_gold_counts(frame: pd.DataFrame) -> None:
    n_rows = len(frame)
    n_gold_0 = int((frame[GOLD_LABEL_COLUMN] == 0).sum())
    n_gold_1 = int((frame[GOLD_LABEL_COLUMN] == 1).sum())
    counts_match = (
        n_rows == SAMPLE_ROW_COUNT
        and n_gold_0 == SAMPLE_GOLD_0_COUNT
        and n_gold_1 == SAMPLE_GOLD_1_COUNT
    )
    if not counts_match:
        raise ValueError(
            f"Expected {SAMPLE_ROW_COUNT} rows ({SAMPLE_GOLD_0_COUNT} gold 0, "
            f"{SAMPLE_GOLD_1_COUNT} gold 1); got {n_rows} ({n_gold_0} gold 0, "
            f"{n_gold_1} gold 1)"
        )


def _sort_sample_frame(frame: pd.DataFrame) -> pd.DataFrame:
    row_ids = frame[ROW_ID_FIELD].astype(int)
    return frame.assign(_row_id_int=row_ids).sort_values("_row_id_int").drop(
        columns="_row_id_int"
    ).reset_index(drop=True)


def load_sample() -> pd.DataFrame:
    """Load the sample parquet, validate manifest and gold counts, and sort rows."""
    sample_path = _local_path(SAMPLE_PARQUET_NAME)
    if not sample_path.is_file():
        raise FileNotFoundError(sample_path)
    validate_manifest(_read_manifest())
    frame = pd.read_parquet(sample_path)
    _validate_gold_counts(frame)
    return _sort_sample_frame(frame)


def load_pr20_jev_labels() -> pd.DataFrame:
    """Load ``data/pr20_jev_labels.parquet``."""
    labels_path = _local_path(PR20_JEV_LABELS_NAME)
    if not labels_path.is_file():
        raise FileNotFoundError(labels_path)
    return pd.read_parquet(labels_path)
