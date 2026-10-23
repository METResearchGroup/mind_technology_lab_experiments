# ruff: noqa: E501
"""Load the TypeSafe API key for Jev grading.

The key is the ``TYPESAFE_API_KEY`` field of Secrets Manager secret
``jev-typesafe-api-key``. ``EnvVarsContainer`` reads it. This module does
not read the process environment.

Run from the repository root (requires AWS credentials for a live run):

    uv run --project experiments/safety_prompting_2026_10_16 python -c "from experiments.safety_prompting_2026_10_16.credentials import load_typesafe_api_key; value = load_typesafe_api_key(); print('ok', len(value) > 0)"
"""

from __future__ import annotations

from lib.load_env_vars import EnvVarsContainer


def load_typesafe_api_key() -> str:
    """Return the TypeSafe key from AWS Secrets Manager. The value is not printed."""
    return EnvVarsContainer.get_env_var("TYPESAFE_API_KEY", required=True)
