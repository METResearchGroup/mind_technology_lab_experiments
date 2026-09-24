# ruff: noqa: E501
"""Load allowlisted secrets for agent scripts without dotenv or os.environ.

Run from the repository root (requires AWS credentials for a live run):

    uv run python -c "from lib.load_env_vars import EnvVarsContainer; value = EnvVarsContainer.get_env_var('GITHUB_PAT_TOKEN', required=True); print('ok', len(value))"
"""

from __future__ import annotations

import threading
from typing import Final

from shared.aws.secretsmanager import load_secret_field, secrets_manager_client

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

        Raises
        ------
        ValueError
            When ``required`` is True and the name is unknown or the value is empty.
        """
        if name in ALLOWLIST:
            instance = cls._get_instance()
            instance._ensure_initialized()
            raw: str | None = instance._env_vars.get(name)
        else:
            raw = None

        if required:
            if raw is None:
                raise ValueError(
                    f"{name} is required but is missing. "
                    f"Please set the {name} environment variable."
                )
            if isinstance(raw, str) and not raw.strip():
                raise ValueError(
                    f"{name} is required but is empty. "
                    f"Please set the {name} environment variable to a non-empty value."
                )

        if raw is None:
            return ""
        return str(raw)

    @classmethod
    def _get_instance(cls) -> EnvVarsContainer:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._initialize_env_vars()
            self._initialized = True

    def _initialize_env_vars(self) -> None:
        client = secrets_manager_client()
        for env_name, (secret_id, field_name) in ALLOWLIST.items():
            self._env_vars[env_name] = load_secret_field(secret_id, field_name, client)
