# ruff: noqa: E501
"""Load an ablation runner by the integer id used on the command line.

Run from the repository root:

    uv run --project experiments/safety_prompting_2026_10_16 python -c "from experiments.safety_prompting_2026_10_16.ablations.registry import load_runner; print(load_runner(1).ablation_id)"
"""

from __future__ import annotations

import importlib

from experiments.safety_prompting_2026_10_16.ablations.interface import AblationRunner

ABLATION_IDS = (1, 2, 3)


def load_runner(ablation: int) -> AblationRunner:
    """Import ``ablations/ablation_{n}/runner.py`` and return its RUNNER.

    Parameters
    ----------
    ablation
        Ablation number, starting at 1.

    Returns
    -------
    AblationRunner
        Runner whose ``ablation_id`` is ``ablation_{n}``.
    """
    if ablation not in ABLATION_IDS:
        known = ", ".join(str(item) for item in ABLATION_IDS)
        raise SystemExit(f"Unknown ablation {ablation}. Known ablations: {known}.")
    module_name = (
        f"experiments.safety_prompting_2026_10_16.ablations.ablation_{ablation}.runner"
    )
    module = importlib.import_module(module_name)
    runner = module.RUNNER
    expected = f"ablation_{ablation}"
    if not isinstance(runner, AblationRunner):
        raise SystemExit(f"{module_name}.RUNNER is not an AblationRunner")
    if runner.ablation_id != expected:
        raise SystemExit(
            f"ablation {ablation} runner id is {runner.ablation_id}, expected {expected}"
        )
    return runner
