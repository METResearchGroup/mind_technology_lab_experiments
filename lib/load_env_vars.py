# ruff: noqa: E501
"""Load allowlisted secrets for agent scripts without dotenv or os.environ.

Run from the repository root (requires AWS credentials for a live run):

    uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('GITHUB_PAT_TOKEN', required=True); print('ok', len(value))"
"""

from __future__ import annotations

import threading
from typing import Final

from shared.aws.secretsmanager import (  # noqa: F401
    load_secret_field,
    secrets_manager_client,
)

ALLOWLIST: Final[dict[str, tuple[str, str]]] = {
    "GITHUB_PAT_TOKEN": ("kova-github-pat", "GITHUB_PAT_TOKEN"),
}


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
        """Get an allowlisted value after container initialization.

        Parameters
        ----------
        name
            Allowlisted environment variable name.
        required
            When True, raise ValueError if the name is unknown or the value is empty.

        Returns
        -------
        str
            Cached secret value, or empty string when optional and missing.
        """
        raise NotImplementedError

    @classmethod
    def _get_instance(cls) -> EnvVarsContainer:
        raise NotImplementedError

    def _ensure_initialized(self) -> None:
        raise NotImplementedError

    def _initialize_env_vars(self) -> None:
        raise NotImplementedError
