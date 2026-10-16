# ruff: noqa: E501
"""Shared runner interface. Every ablation module exports a RUNNER of this type.

Run from the repository root:

    uv run --project experiments/safety_prompting_2026_10_16 python -c "from experiments.safety_prompting_2026_10_16.ablations.interface import SystemPromptRunner; print(SystemPromptRunner.__name__)"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from experiments.safety_prompting_2026_10_16.ablations.ollama import (
    MODEL_NAME,
    Generation,
    generate,
)


@runtime_checkable
class AblationRunner(Protocol):
    """What ``run.py`` needs from an ablation."""

    ablation_id: str
    system_prompt: str

    def complete(self, user_prompt: str) -> Generation:
        """Return the model response for one user prompt."""


@dataclass(frozen=True)
class SystemPromptRunner:
    """Ablation that only changes the system prompt sent to Ollama."""

    ablation_id: str
    system_prompt: str
    model: str = MODEL_NAME

    def complete(self, user_prompt: str) -> Generation:
        """Generate one response with this ablation's system prompt.

        An empty system prompt is the control: the chat request contains only
        the user message.
        """
        return generate(self.model, self.system_prompt, user_prompt)
