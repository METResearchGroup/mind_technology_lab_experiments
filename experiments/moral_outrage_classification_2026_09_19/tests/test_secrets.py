"""Tests for Secrets Manager field loading. Never assert live key values."""

import logging
from types import SimpleNamespace

import pytest

from shared.secrets import TYPESAFE_FIELD_NAME, TYPESAFE_SECRET_ID, load_secret_field


class _FakeSecretsClient:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def get_secret_value(self, SecretId: str) -> dict[str, str]:
        return {"SecretString": self._payload, "Name": SecretId}


class TestLoadSecretField:
    """Tests for load_secret_field()."""

    def test_returns_named_field_without_logging_value(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A matching JSON field is returned and the value is not logged."""
        secret_value = "abc"
        client = _FakeSecretsClient(f'{{"{TYPESAFE_FIELD_NAME}":"{secret_value}"}}')

        with caplog.at_level(logging.DEBUG):
            result = load_secret_field(TYPESAFE_SECRET_ID, TYPESAFE_FIELD_NAME, client)

        assert result == secret_value
        assert secret_value not in caplog.text

    def test_missing_field_raises_system_exit_with_secret_name(self) -> None:
        """Missing JSON field raises SystemExit naming the secret, not a value."""
        client = _FakeSecretsClient('{"OTHER_KEY":"abc"}')

        with pytest.raises(SystemExit) as exc_info:
            load_secret_field(TYPESAFE_SECRET_ID, TYPESAFE_FIELD_NAME, client)

        assert TYPESAFE_SECRET_ID in str(exc_info.value)
