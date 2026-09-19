"""Download the Brady labeled CSV, validate it, and write the 1,000-row sample.

Run from the experiment folder:

    uv run python -c "from shared.data import download_full_csv, load_full_frame, write_sample_if_missing; from shared.aws_region import AWS_REGION; print(AWS_REGION); p=download_full_csv(); df=load_full_frame(p); print(len(df), int((df.gold_label==0).sum()), int((df.gold_label==1).sum())); write_sample_if_missing(df)"
"""

from pathlib import Path

import pandas as pd


def download_full_csv(destination: Path) -> Path:
    """Download the 26,000-row Brady CSV to the given path."""
    raise NotImplementedError


def load_full_frame(csv_path: Path) -> pd.DataFrame:
    """Parse the full CSV into source_row_id, text, gold_label, tweet_id."""
    raise NotImplementedError


def validate_full_frame(frame: pd.DataFrame) -> None:
    """Fail if the frame is not 26,000 rows with 14,563 zeros and 11,437 ones."""
    raise NotImplementedError


def draw_stratified_sample(
    frame: pd.DataFrame,
    n_gold_0: int,
    n_gold_1: int,
    seed: int,
) -> pd.DataFrame:
    """Draw a stratified sample with explicit per-class counts."""
    raise NotImplementedError


def write_sample_if_missing(frame: pd.DataFrame) -> Path:
    """Write the 1,000-row sample and manifest once, then reuse them."""
    raise NotImplementedError


def load_sample() -> pd.DataFrame:
    """Load the on-disk 1,000-row sample."""
    raise NotImplementedError
