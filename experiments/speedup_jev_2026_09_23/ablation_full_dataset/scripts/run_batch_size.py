"""Run one full ablation pass for a batch size and write pass outputs.

Run from the experiment folder:

    uv run python ablation_full_dataset/scripts/run_batch_size.py --batch-size 20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from models.batched_jev import build_live_scorer  # noqa: E402
from scripts.run_batch_size import finalize_pass_outputs  # noqa: E402
from shared.batch_runner import run_pass  # noqa: E402
from shared.full_dataset import (  # noqa: E402
    ABLATION_BATCH_SIZES,
    SHUFFLE_SEED,
    shuffled_tasks,
)
from shared.rate_limiter import (  # noqa: E402
    MAX_REQUEST_STARTS_PER_MINUTE,
    RequestStartLimiter,
)
from shared.secrets import load_typesafe_api_key  # noqa: E402

ABLATION_ROOT = EXPERIMENT_ROOT / "ablation_full_dataset"
OUTPUTS_ROOT = ABLATION_ROOT / "outputs"


def main() -> None:
    """Parse args, run one ablation pass, and write pass outputs."""
    batch_size = _parse_batch_size()
    tasks = shuffled_tasks(SHUFFLE_SEED)
    output_dir = _output_dir(batch_size)
    scorer = build_live_scorer(load_typesafe_api_key())
    limiter = RequestStartLimiter(MAX_REQUEST_STARTS_PER_MINUTE)
    run_pass(tasks, batch_size, output_dir, scorer, limiter)
    finalize_pass_outputs(batch_size, output_dir)


def _parse_batch_size() -> int:
    """Parse and validate the required ``--batch-size`` CLI argument."""
    parser = argparse.ArgumentParser(description="Run one ablation batch-size pass.")
    parser.add_argument(
        "--batch-size",
        type=int,
        choices=ABLATION_BATCH_SIZES,
        required=True,
        help=f"Posts per request; allowed values: {ABLATION_BATCH_SIZES}",
    )
    return parser.parse_args().batch_size


def _output_dir(batch_size: int) -> Path:
    """Return the output directory for one ablation batch-size pass."""
    return OUTPUTS_ROOT / f"batch_{batch_size}"


if __name__ == "__main__":
    main()
