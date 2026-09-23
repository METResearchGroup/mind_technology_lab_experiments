"""Send one single-post Jev request to confirm the TypeSafe key works.

Run from the experiment folder:

    uv run python scripts/check_typesafe_key.py
"""

from __future__ import annotations

import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent.parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))


def main() -> None:
    """Load the key, score the first sample post, and print an ok line."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
