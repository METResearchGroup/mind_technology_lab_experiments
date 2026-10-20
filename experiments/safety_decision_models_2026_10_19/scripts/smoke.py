"""Twenty-item smoke test per arm (implemented in step 3).

Run from the experiment folder:

    uv run python scripts/smoke.py
"""

from __future__ import annotations

"""
Later smoke checks (step 3), one list per arm (jev, clef, clef-flash, guardrails):

1. Load 20 development items end-to-end for the arm.
2. Each returned row includes all ExampleRecord-derived fields on the prediction path.
3. Jev, Clef, and Clef-flash rows have a non-empty probability.
4. Guardrails rows have a non-empty band (NONE, LOW, MEDIUM, or HIGH).
5. Second pass of the same 20 items must hit the SQLite cache with zero new provider calls.
6. Jev smoke primary metric must be comparable to the published harness metric.
7-20. Repeat items 1-6 across representative datasets in the core pack until
      twenty assertions are recorded in the smoke log for that arm.

This step keeps the script as a stub: exit 0 without calling providers.
"""


def main() -> None:
    """Stub entry point until step 3 wires the smoke harness."""
    print("smoke stub: see module docstring for the 20 planned checks")


if __name__ == "__main__":
    main()
