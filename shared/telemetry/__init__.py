"""Telemetry helpers shared across repository experiments.

Run from the repository root:

    uv run python -c "from shared.telemetry import start_run; print(start_run)"
"""

from shared.telemetry.wandb import ENTITY, ORGANIZATION, start_run

__all__ = ["ENTITY", "ORGANIZATION", "start_run"]
