# ruff: noqa: E501
"""Ablation 3 runner.

Run from the repository root:

    uv run --project experiments/safety_prompting_2026_10_16 python -c "from experiments.safety_prompting_2026_10_16.ablations.ablation_3.runner import RUNNER; print(repr(RUNNER.system_prompt))"
"""

from experiments.safety_prompting_2026_10_16.ablations.interface import (
    SystemPromptRunner,
)

SYSTEM_PROMPT = ""

RUNNER = SystemPromptRunner(ablation_id="ablation_3", system_prompt=SYSTEM_PROMPT)
