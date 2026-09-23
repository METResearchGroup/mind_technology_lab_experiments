"""Download PR 20 inputs from S3 and print sample summary lines.

Run from the experiment folder:

    uv run python scripts/fetch_inputs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from shared.data import (  # noqa: E402
    SAMPLE_GOLD_0_COUNT,
    SAMPLE_GOLD_1_COUNT,
    SAMPLE_ROW_COUNT,
    SAMPLE_SEED,
    download_inputs,
    load_pr20_jev_labels,
    load_sample,
)


def main() -> None:
    """Download inputs, load sample and PR 20 labels, and print counts."""
    download_inputs()
    sample = load_sample()
    labels = load_pr20_jev_labels()
    print(
        f"sample rows={len(sample)} gold_0={SAMPLE_GOLD_0_COUNT} "
        f"gold_1={SAMPLE_GOLD_1_COUNT} seed={SAMPLE_SEED}"
    )
    print(f"pr20 jev rows={len(labels)}")


if __name__ == "__main__":
    main()
