# ruff: noqa: E501
"""Load prompt markdown from this package.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "from workflow.prompts import load_prompt; print(len(load_prompt('templates/seed.md')))"
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(relative_path: str) -> str:
    """Read one UTF-8 prompt file under this package.

    Parameters
    ----------
    relative_path
        Path relative to ``workflow/prompts``.

    Returns
    -------
    str
        File text.

    Raises
    ------
    ValueError
        When the path resolves outside this package.
    FileNotFoundError
        When the file does not exist.
    """
    candidate = (_PROMPTS_DIR / relative_path).resolve()
    try:
        candidate.relative_to(_PROMPTS_DIR)
    except ValueError as exc:
        message = f"prompt path leaves prompts directory: {relative_path}"
        raise ValueError(message) from exc
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate.read_text(encoding="utf-8")
