"""Write ablation RESULTS after all full passes complete.

Run from the experiment folder:

    uv run python ablation_full_dataset/scripts/write_results.py
"""

from __future__ import annotations

import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))


def main() -> None:
    """Stub until step 4 fills ablation RESULTS."""
    raise SystemExit("write_results.py is not implemented yet.")


if __name__ == "__main__":
    main()
