"""Unit tests for lib.load_env_vars."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from lib.load_env_vars import EnvVarsContainer


@pytest.fixture(autouse=True)
def reset_env_container() -> Iterator[None]:
    """Clear the singleton so each test runs initialization in isolation."""
    EnvVarsContainer._instance = None
    yield
    EnvVarsContainer._instance = None


class TestGetEnvVar:
    """Tests for EnvVarsContainer.get_env_var."""

    def test_required_present(self) -> None:
        """Required allowlisted name returns the patched secret value."""
        with patch(
            "lib.load_env_vars.load_secret_field", return_value="fake-token"
        ) as mock_load:
            with patch("lib.load_env_vars.secrets_manager_client") as mock_client:
                mock_client.return_value = MagicMock()

                result = EnvVarsContainer.get_env_var("GITHUB_PAT_TOKEN", required=True)

        assert result == "fake-token"
        mock_load.assert_called_once_with(
            "kova-github-pat",
            "GITHUB_PAT_TOKEN",
            mock_client.return_value,
        )

    def test_required_missing_unknown_name(self) -> None:
        """Required unknown name raises ValueError with the missing message."""
        with pytest.raises(ValueError) as exc_info:
            EnvVarsContainer.get_env_var("UNKNOWN_VAR", required=True)

        assert "UNKNOWN_VAR is required but is missing" in str(exc_info.value)

    def test_required_empty_cached(self) -> None:
        """Required allowlisted name raises when cached value is blank."""
        with patch("lib.load_env_vars.load_secret_field", return_value=""):
            with patch("lib.load_env_vars.secrets_manager_client"):
                with pytest.raises(ValueError) as exc_info:
                    EnvVarsContainer.get_env_var("GITHUB_PAT_TOKEN", required=True)

        assert "GITHUB_PAT_TOKEN is required but is empty" in str(exc_info.value)

        EnvVarsContainer._instance = None
        with patch("lib.load_env_vars.load_secret_field", return_value="   "):
            with patch("lib.load_env_vars.secrets_manager_client"):
                with pytest.raises(ValueError) as exc_info:
                    EnvVarsContainer.get_env_var("GITHUB_PAT_TOKEN", required=True)

        assert "GITHUB_PAT_TOKEN is required but is empty" in str(exc_info.value)

    def test_optional_missing_unknown(self) -> None:
        """Optional unknown name returns empty string without calling AWS."""
        with patch("lib.load_env_vars.load_secret_field") as mock_load:
            result = EnvVarsContainer.get_env_var("NOT_IN_ALLOWLIST", required=False)

        assert result == ""
        mock_load.assert_not_called()

    def test_optional_missing_allowlisted_empty(self) -> None:
        """Optional allowlisted name returns empty string when secret is blank."""
        with patch("lib.load_env_vars.load_secret_field", return_value=""):
            with patch("lib.load_env_vars.secrets_manager_client"):
                result = EnvVarsContainer.get_env_var(
                    "GITHUB_PAT_TOKEN", required=False
                )

        assert result == ""

    def test_optional_whitespace_only_cached(self) -> None:
        """Optional allowlisted name returns '' when cached value is whitespace-only."""
        with patch("lib.load_env_vars.load_secret_field", return_value="   "):
            with patch("lib.load_env_vars.secrets_manager_client"):
                result = EnvVarsContainer.get_env_var(
                    "GITHUB_PAT_TOKEN", required=False
                )

        assert result == ""

    def test_initialization_calls_load_secret_field(self) -> None:
        """First access loads each allowlisted secret exactly once."""
        client = MagicMock()
        with patch(
            "lib.load_env_vars.load_secret_field", return_value="token"
        ) as mock_load:
            with patch("lib.load_env_vars.secrets_manager_client", return_value=client):
                EnvVarsContainer.get_env_var("GITHUB_PAT_TOKEN")
                EnvVarsContainer.get_env_var("GITHUB_PAT_TOKEN")

        mock_load.assert_called_once_with("kova-github-pat", "GITHUB_PAT_TOKEN", client)
