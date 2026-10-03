"""Start Weights & Biases runs for Mind Technology Lab experiments.

Run from the repository root:

    uv run python -c "from shared.telemetry.wandb import ENTITY; print(ENTITY)"
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import wandb

# The organization holds the lab's teams. The entity is the team that owns
# projects, which is the namespace already used by lab runs.
ORGANIZATION = "mind_technology_lab-org"
ENTITY = "mind_technology_lab"


def start_run(
    project: str,
    group: str,
    name: str,
    *,
    config: Mapping[str, Any] | None = None,
) -> wandb.Run:
    """Open a run in the lab organization and team.

    Parameters
    ----------
    project
        Project name. Runs in one project share a table and charts.
    group
        Group name for runs that belong to one experiment.
    name
        Display name of this run, for example ``R5_gepa_original_test_eval``.
    config
        Optional inputs stored on the run, such as hyperparameters.

    Returns
    -------
    wandb.Run
        The active run. Use it as a context manager so the run finishes on exit.

    Raises
    ------
    ValueError
        When ``project``, ``group``, or ``name`` is blank.
    RuntimeError
        When ``wandb.init`` does not return a run.
    """
    _require_text("project", project)
    _require_text("group", group)
    _require_text("name", name)

    # Libraries that call wandb.init later in this process, such as TRL with
    # report_to="wandb", read these variables.
    os.environ["WANDB_ORGANIZATION"] = ORGANIZATION
    os.environ["WANDB_ENTITY"] = ENTITY
    os.environ["WANDB_PROJECT"] = project
    os.environ["WANDB_RUN_GROUP"] = group
    os.environ["WANDB_NAME"] = name

    settings = wandb.Settings(
        organization=ORGANIZATION,
        entity=ENTITY,
        project=project,
        run_group=group,
        run_name=name,
    )
    run = wandb.init(
        entity=ENTITY,
        project=project,
        group=group,
        name=name,
        config=dict(config) if config is not None else None,
        settings=settings,
    )
    if run is None:
        raise RuntimeError(
            "wandb.init did not return a run. "
            "Set WANDB_API_KEY, and leave WANDB_MODE unset or set it to online."
        )
    return run


def _require_text(label: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
