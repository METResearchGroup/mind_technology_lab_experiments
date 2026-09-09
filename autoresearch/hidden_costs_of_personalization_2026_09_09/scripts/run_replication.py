#!/usr/bin/env python3
"""Entry point that does not require the package to be installed."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prisk.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
