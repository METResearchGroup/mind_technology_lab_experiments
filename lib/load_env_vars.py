# ruff: noqa: E501
"""Load allowlisted secrets for agent scripts without dotenv or os.environ.

Run from the repository root (requires AWS credentials for a live run):

    uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('GITHUB_PAT_TOKEN', required=True); print('ok', len(value))"
"""

from __future__ import annotations

import threading


class EnvVarsContainer:
    """Thread-safe singleton container for allowlisted environment values."""

    _instance: EnvVarsContainer | None = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._initialized = False
        self._env_vars: dict[str, str | None] = {}
        self._init_lock = threading.Lock()

    @classmethod
    def get_env_var(cls, name: str, required: bool = False) -> str:
        """Return an allowlisted value after one-time initialization."""
        raise NotImplementedError
