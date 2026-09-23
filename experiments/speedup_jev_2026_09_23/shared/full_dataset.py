"""Download, validate, and shuffle the full 26k Brady training CSV.

Run from the experiment folder:

    uv run python ablation_full_dataset/scripts/fetch_full_dataset.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from shared.aws_region import AWS_REGION
from shared.records import PostTask
from shared.secrets import build_boto3_session

SOURCE_BUCKET = "met-research-group-datasets"
SOURCE_KEY = "moral_outrage_classifier/26k_training_data.csv"
SOURCE_URI = "s3://met-research-group-datasets/moral_outrage_classifier/26k_training_data.csv"
FULL_CSV_NAME = "26k_training_data.csv"
TEXT_COLUMN = "text"
GOLD_COLUMN = "outrage"
ROW_ID_FIELD = "source_row_id"
GOLD_LABEL_COLUMN = "gold_label"
FULL_ROW_COUNT = 26000
FULL_GOLD_0_COUNT = 14563
FULL_GOLD_1_COUNT = 11437
SHUFFLE_SEED = 20260923
ABLATION_BATCH_SIZES = (10, 20, 40, 60, 80)
ABLATION_ROOT = Path(__file__).resolve().parent.parent / "ablation_full_dataset"
DATA_DIR = ABLATION_ROOT / "data"
DEFAULT_CSV_PATH = DATA_DIR / FULL_CSV_NAME


def download_full_csv(destination: Path) -> Path:
    """Download the 26,000-row Brady CSV when it is not already on disk.

    Parameters
    ----------
    destination
        Local path for the CSV.

    Returns
    -------
    Path
        Path to the local CSV.
    """
    if destination.is_file():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    session = build_boto3_session()
    client = session.client("s3", region_name=AWS_REGION)
    client.download_file(SOURCE_BUCKET, SOURCE_KEY, str(destination))
    return destination


def load_full_frame(csv_path: Path) -> pd.DataFrame:
    """Parse the full CSV into ``source_row_id``, ``text``, and ``gold_label``.

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
    raw = pd.read_csv(csv_path)
    missing_columns = {TEXT_COLUMN, GOLD_COLUMN} - set(raw.columns)
    if missing_columns:
        raise ValueError(f"CSV missing columns: {sorted(missing_columns)}")
    frame = pd.DataFrame(
        {
            ROW_ID_FIELD: [str(index) for index in range(len(raw))],
            TEXT_COLUMN: raw[TEXT_COLUMN].astype(str),
            GOLD_LABEL_COLUMN: raw[GOLD_COLUMN].astype(int),
        }
    )
    validate_full_frame(frame)
    return frame


def validate_full_frame(frame: pd.DataFrame) -> None:
    """Fail when row count or gold-label mix does not match the locked file.

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
    n_gold_0 = int((frame[GOLD_LABEL_COLUMN] == 0).sum())
    n_gold_1 = int((frame[GOLD_LABEL_COLUMN] == 1).sum())
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


def shuffled_frame(seed: int) -> pd.DataFrame:
    """Return the full validated frame in one reproducible shuffle order.

    Parameters
    ----------
    seed
        Seed for ``numpy.random.Generator``.

    Returns
    -------
    pd.DataFrame
        Shuffled frame with ``source_row_id``, ``text``, and ``gold_label``.
    """
    frame = load_full_frame(DEFAULT_CSV_PATH)
    order = np.random.default_rng(seed).permutation(len(frame))
    return frame.iloc[order].reset_index(drop=True)


def shuffled_tasks(seed: int) -> list[PostTask]:
    """Return all posts as tasks in one reproducible shuffle order.

    Parameters
    ----------
    seed
        Seed for ``numpy.random.Generator``.

    Returns
    -------
    list[PostTask]
        Tasks in shuffle order.
    """
    frame = shuffled_frame(seed)
    return _frame_to_tasks(frame)


def _frame_to_tasks(frame: pd.DataFrame) -> list[PostTask]:
    """Convert a labeled frame into scoring tasks preserving row order."""
    tasks: list[PostTask] = []
    for row in frame.itertuples(index=False):
        tasks.append(
            PostTask(
                source_row_id=str(getattr(row, ROW_ID_FIELD)),
                text=str(getattr(row, TEXT_COLUMN)),
                gold_label=int(getattr(row, GOLD_LABEL_COLUMN)),
            )
        )
    return tasks
