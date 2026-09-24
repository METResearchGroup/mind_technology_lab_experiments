from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

from shared.aws.s3 import DEFAULT_REGION_NAME, S3

BUCKET = "met-research-group-datasets"
S3_KEY = "moral_outrage_classifier/26k_training_data.csv"
SAMPLE_ROWS = 1000
LOCAL_DIR = Path(__file__).resolve().parent
FILENAME = Path(S3_KEY).name
STEM = Path(S3_KEY).stem

LoadMode = Literal["full", "sample"]


class DataLoader:
    """Load the moral-outrage training CSV into memory from local disk or S3."""

    def __init__(self) -> None:
        self._local_dir = LOCAL_DIR
        self._full_path = self._local_dir / FILENAME
        self._sample_path = self._local_dir / f"{STEM}_{SAMPLE_ROWS}.csv"

    def load_data(self, mode: LoadMode) -> pd.DataFrame:
        """Return the full dataset, or the first 1,000 rows.

        Parameters
        ----------
        mode
            ``"full"`` returns every row. ``"sample"`` returns the first 1,000
            rows and writes them to ``{stem}_1000.csv`` if that file is missing.

        The full CSV is always loaded into memory. If
        ``cookbooks/how_to_use_wandb/shared/setup/{filename}.csv`` is absent,
        the object is fetched from S3 and written there first.
        """
        if mode not in ("full", "sample"):
            raise ValueError(f"mode must be 'full' or 'sample', got {mode!r}")

        frame = self._load_full_dataset()
        if mode == "full":
            return frame

        sample = frame.head(SAMPLE_ROWS)
        if not self._sample_path.exists():
            sample.to_csv(self._sample_path, index=False)
        return sample

    def _load_full_dataset(self) -> pd.DataFrame:
        if self._full_path.exists():
            return pd.read_csv(self._full_path)

        client = S3(BUCKET, region_name=DEFAULT_REGION_NAME)
        frame = client.load_csv_to_dataframe(S3_KEY)
        self._local_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(self._full_path, index=False)
        return frame
