"""Download the Brady labeled CSV, validate it, and write the 1,000-row sample.

Run from the experiment folder:

    uv run python -c "from shared.data import download_full_csv, load_full_frame, write_sample_if_missing; from shared.aws_region import AWS_REGION; print(AWS_REGION); p=download_full_csv(); df=load_full_frame(p); print(len(df), int((df.gold_label==0).sum()), int((df.gold_label==1).sum())); write_sample_if_missing(df)"
"""

import json
import os
from pathlib import Path

import boto3
import numpy as np
import pandas as pd

from shared.aws_region import AWS_REGION
from shared.secrets import (
    ACCESS_KEY_ID_ENV,
    ACCESS_KEY_SECRET_ENV,
    LAB_ACCESS_KEY_ID_ENV,
    LAB_SECRET_ACCESS_KEY_ENV,
    SECRET_ACCESS_KEY_ENV,
)

SOURCE_URI = (
    "s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv"
)
SOURCE_BUCKET = "met-research-group-datasets"
SOURCE_KEY = "moral_outrage_classifier/26k_training_data.csv"
TEXT_COLUMN = "text"
GOLD_COLUMN = "outrage"
TWEET_ID_COLUMN = "tweet_id"
ROW_ID_FIELD = "source_row_id"
FULL_ROW_COUNT = 26000
FULL_GOLD_0_COUNT = 14563
FULL_GOLD_1_COUNT = 11437
SAMPLE_ROW_COUNT = 1000
SAMPLE_GOLD_0_COUNT = 560
SAMPLE_GOLD_1_COUNT = 440
SAMPLE_SEED = 20260919
SAMPLE_PARQUET_NAME = "sample_1000.parquet"
SAMPLE_MANIFEST_NAME = "sample_1000.manifest.json"
FULL_CSV_NAME = "26k_training_data.csv"
EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = EXPERIMENT_ROOT / "data"


def _resolve_aws_access_keys() -> tuple[str, str]:
    lab_access_key_id = os.environ.get(LAB_ACCESS_KEY_ID_ENV, "")
    lab_secret_access_key = os.environ.get(LAB_SECRET_ACCESS_KEY_ENV, "")
    if lab_access_key_id and lab_secret_access_key:
        return lab_access_key_id, lab_secret_access_key
    access_key_id = os.environ.get(ACCESS_KEY_ID_ENV, "")
    secret_access_key = os.environ.get(SECRET_ACCESS_KEY_ENV, "")
    if not secret_access_key:
        secret_access_key = os.environ.get(ACCESS_KEY_SECRET_ENV, "")
    return access_key_id, secret_access_key


def _s3_client() -> object:
    access_key_id, secret_access_key = _resolve_aws_access_keys()
    session_kwargs: dict[str, str] = {"region_name": AWS_REGION}
    if access_key_id and secret_access_key:
        session_kwargs["aws_access_key_id"] = access_key_id
        session_kwargs["aws_secret_access_key"] = secret_access_key
    session = boto3.session.Session(**session_kwargs)
    return session.client("s3", region_name=AWS_REGION)


def download_full_csv(destination: Path | None = None) -> Path:
    """Download the 26,000-row Brady CSV if it is not already on disk.

    Parameters
    ----------
    destination
        Local path for the CSV. Defaults to ``data/26k_training_data.csv``.

    Returns
    -------
    Path
        Path to the local CSV.
    """
    csv_path = DATA_DIR / FULL_CSV_NAME if destination is None else destination
    if csv_path.is_file():
        return csv_path
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    client = _s3_client()
    client.download_file(SOURCE_BUCKET, SOURCE_KEY, str(csv_path))
    return csv_path


def load_full_frame(csv_path: Path) -> pd.DataFrame:
    """Parse the full CSV into source_row_id, text, gold_label, tweet_id.

    Parameters
    ----------
    csv_path
        Path to the downloaded 26,000-row CSV.

    Returns
    -------
    pd.DataFrame
        Parsed frame with integer gold labels and string row ids.

    Raises
    ------
    ValueError
        When the file is missing required columns or fails count checks.
    """
    raw = pd.read_csv(csv_path, dtype={TWEET_ID_COLUMN: "string"})
    missing_columns = {TEXT_COLUMN, GOLD_COLUMN} - set(raw.columns)
    if missing_columns:
        raise ValueError(f"CSV missing columns: {sorted(missing_columns)}")
    frame = pd.DataFrame(
        {
            ROW_ID_FIELD: [str(i) for i in range(len(raw))],
            "text": raw[TEXT_COLUMN].astype(str),
            "gold_label": raw[GOLD_COLUMN].astype(int),
            "tweet_id": raw[TWEET_ID_COLUMN]
            if TWEET_ID_COLUMN in raw.columns
            else pd.Series([pd.NA] * len(raw), dtype="string"),
        }
    )
    validate_full_frame(frame)
    return frame


def validate_full_frame(frame: pd.DataFrame) -> None:
    """Fail if the frame is not 26,000 rows with 14,563 zeros and 11,437 ones.

    Parameters
    ----------
    frame
        Parsed frame with a ``gold_label`` column.

    Raises
    ------
    ValueError
        When the row count or gold-label mix does not match the locked file.
    """
    n_rows = len(frame)
    n_gold_0 = int((frame.gold_label == 0).sum())
    n_gold_1 = int((frame.gold_label == 1).sum())
    counts_match = (
        n_rows == FULL_ROW_COUNT
        and n_gold_0 == FULL_GOLD_0_COUNT
        and n_gold_1 == FULL_GOLD_1_COUNT
    )
    if not counts_match:
        raise ValueError(
            f"Expected {FULL_ROW_COUNT} rows ({FULL_GOLD_0_COUNT} gold 0, "
            f"{FULL_GOLD_1_COUNT} gold 1); got {n_rows} ({n_gold_0} gold 0, "
            f"{n_gold_1} gold 1)"
        )


def draw_stratified_sample(
    frame: pd.DataFrame,
    n_gold_0: int,
    n_gold_1: int,
    seed: int,
) -> pd.DataFrame:
    """Draw a stratified sample with explicit per-class counts.

    Parameters
    ----------
    frame
        Parsed labeled frame.
    n_gold_0
        Number of gold-0 rows to keep.
    n_gold_1
        Number of gold-1 rows to keep.
    seed
        Seed for ``numpy.random.Generator``.

    Returns
    -------
    pd.DataFrame
        Sample sorted by ``source_row_id``.
    """
    rng = np.random.default_rng(seed)
    gold_0 = _sample_class(frame, gold_label=0, n_rows=n_gold_0, rng=rng)
    gold_1 = _sample_class(frame, gold_label=1, n_rows=n_gold_1, rng=rng)
    combined = pd.concat([gold_0, gold_1], ignore_index=True)
    return combined.sort_values(ROW_ID_FIELD).reset_index(drop=True)


def _sample_class(
    frame: pd.DataFrame,
    gold_label: int,
    n_rows: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    class_rows = frame.loc[frame.gold_label == gold_label].reset_index(drop=True)
    if len(class_rows) < n_rows:
        raise ValueError(
            f"Need {n_rows} gold {gold_label} rows; found {len(class_rows)}"
        )
    order = rng.permutation(len(class_rows))
    return class_rows.iloc[order[:n_rows]]


def _sample_paths() -> tuple[Path, Path]:
    return DATA_DIR / SAMPLE_PARQUET_NAME, DATA_DIR / SAMPLE_MANIFEST_NAME


def _manifest_matches(manifest: dict[str, object]) -> bool:
    expected = {
        "source_uri": SOURCE_URI,
        "seed": SAMPLE_SEED,
        "n_rows": SAMPLE_ROW_COUNT,
        "n_gold_0": SAMPLE_GOLD_0_COUNT,
        "n_gold_1": SAMPLE_GOLD_1_COUNT,
        "row_id_field": ROW_ID_FIELD,
    }
    return manifest == expected


def write_sample_if_missing(frame: pd.DataFrame) -> Path:
    """Write the 1,000-row sample and manifest once, then reuse them.

    Parameters
    ----------
    frame
        Validated full labeled frame.

    Returns
    -------
    Path
        Path to ``data/sample_1000.parquet``.
    """
    sample_path, manifest_path = _sample_paths()
    if sample_path.is_file() and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if _manifest_matches(manifest):
            return sample_path
    sample = draw_stratified_sample(
        frame, SAMPLE_GOLD_0_COUNT, SAMPLE_GOLD_1_COUNT, SAMPLE_SEED
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sample.to_parquet(sample_path, index=False)
    manifest = {
        "source_uri": SOURCE_URI,
        "seed": SAMPLE_SEED,
        "n_rows": SAMPLE_ROW_COUNT,
        "n_gold_0": SAMPLE_GOLD_0_COUNT,
        "n_gold_1": SAMPLE_GOLD_1_COUNT,
        "row_id_field": ROW_ID_FIELD,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return sample_path


def load_sample() -> pd.DataFrame:
    """Load the on-disk 1,000-row sample."""
    sample_path, _manifest_path = _sample_paths()
    if not sample_path.is_file():
        raise FileNotFoundError(sample_path)
    return pd.read_parquet(sample_path)
