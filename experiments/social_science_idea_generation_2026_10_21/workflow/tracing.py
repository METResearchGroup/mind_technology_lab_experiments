# ruff: noqa: E501
"""Configure LangSmith tracing via environment variables.

Run from the repository root:

    PYTHONPATH=/workspace:/workspace/experiments/social_science_idea_generation_2026_10_21 \\
      uv run --project experiments/social_science_idea_generation_2026_10_21 \\
      python -c "from workflow.tracing import configure_tracing; print('ok')"
"""

import os

from workflow.constants import LANGSMITH_PROJECT


def configure_tracing(langsmith_api_key: str) -> None:
    """Enable LangSmith tracing before any model calls.

    Parameters
    ----------
    langsmith_api_key
        LangSmith API key (written to ``LANGSMITH_API_KEY`` only).
    """
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
