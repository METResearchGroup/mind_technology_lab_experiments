"""Download and validate the full 26k training CSV for the ablation.

Run from the experiment folder:

    uv run python ablation_full_dataset/scripts/fetch_full_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.full_dataset import (  # noqa: E402
    DEFAULT_CSV_PATH,
    FULL_GOLD_0_COUNT,
    FULL_GOLD_1_COUNT,
    FULL_ROW_COUNT,
    SHUFFLE_SEED,
    download_full_csv,
    load_full_frame,
    validate_full_frame,
)


def main() -> None:
    """Download the CSV, validate counts, and print the locked summary lines."""
    csv_path = download_full_csv(DEFAULT_CSV_PATH)
    frame = load_full_frame(csv_path)
    validate_full_frame(frame)
    print(
        f"full rows={FULL_ROW_COUNT} gold_0={FULL_GOLD_0_COUNT} "
        f"gold_1={FULL_GOLD_1_COUNT}"
    )
    print(f"shuffle_seed={SHUFFLE_SEED}")


if __name__ == "__main__":
    main()
