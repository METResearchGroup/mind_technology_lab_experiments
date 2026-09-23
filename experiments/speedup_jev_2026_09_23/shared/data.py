"""Download the PR 20 sample from S3 and validate the manifest.

Run from the experiment folder:

    uv run python -c "from shared.data import download_inputs; download_inputs()"
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

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


def download_inputs() -> None:
    """Download each PR 20 input file that is not already on disk."""
    raise NotImplementedError


def validate_manifest(manifest: dict[str, object]) -> None:
    """Raise ``ValueError`` when manifest fields differ from locked constants."""
    raise NotImplementedError


def load_sample() -> pd.DataFrame:
    """Load the sample parquet, validate manifest and gold counts, and sort rows."""
    raise NotImplementedError


def load_pr20_jev_labels() -> pd.DataFrame:
    """Load ``data/pr20_jev_labels.parquet``."""
    raise NotImplementedError
