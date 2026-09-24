# ruff: noqa: E501
"""Repository-root helpers shared across experiments.

This package holds small utilities (for example environment variable loading)
that agents and scripts import from the repository root.

Run from the repository root:

    uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('GH_TOKEN', required=True); print('ok', len(value))"
"""
