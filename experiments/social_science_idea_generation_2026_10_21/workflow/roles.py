# ruff: noqa: E501
"""Disciplinary seed order and staff roles for one discussion.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "from workflow.roles import ROLE_ORDER; print(len(ROLE_ORDER))"
"""

from dataclasses import dataclass

from workflow.prompts import load_prompt


@dataclass(frozen=True)
class RoleSpec:
    """One speaker. ``system_prompt`` is the persona file for ``role_id``."""

    role_id: str
    display_name: str
    system_prompt: str


def _role(role_id: str, display_name: str) -> RoleSpec:
    prompt_path = f"personas/{role_id}.md"
    return RoleSpec(
        role_id=role_id,
        display_name=display_name,
        system_prompt=load_prompt(prompt_path),
    )


ROLE_ORDER: tuple[RoleSpec, ...] = (
    _role("social_psychologist", "Social psychologist"),
    _role("computer_scientist", "Computer scientist"),
    _role("communications_researcher", "Communications researcher"),
    _role("sociologist", "Sociologist"),
    _role("political_scientist", "Political scientist"),
)

SYNTHESIZER = _role("synthesizer", "Synthesizer")
METHODOLOGIST = _role("methodologist", "Methodologist")
CRITIC = _role("critic", "Critic")
