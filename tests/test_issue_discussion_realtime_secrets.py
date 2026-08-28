"""Tests for issue_discussion_platform realtime_secrets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import APIStatusError, OpenAI

from issue_discussion_platform.prompts import SYSTEM_PROMPT
from issue_discussion_platform.realtime_secrets import (
    CLIENT_SECRETS_PATH,
    RealtimeClientSecretError,
    build_realtime_session_config,
    create_realtime_client_secret,
)
from issue_discussion_platform.voice_agent import (
    INPUT_TRANSCRIPTION_MODEL,
    OUTPUT_VOICE,
    REALTIME_MODEL,
)


def _fake_openai_api_key(name: str, required: bool = False) -> str:
    assert name == "OPENAI_API_KEY"
    return "sk-test-server-key"


@dataclass
class _FakeClientSecretResponse:
    value: str
    expires_at: int


def test_build_realtime_session_config_shape() -> None:
    session = build_realtime_session_config()

    assert session["type"] == "realtime"
    assert session["model"] == REALTIME_MODEL
    assert session["model"] == "gpt-realtime-2.1"
    assert session["reasoning"] == {"effort": "low"}
    assert session["instructions"] == SYSTEM_PROMPT
    assert session["audio"]["input"]["turn_detection"] == {"type": "semantic_vad"}
    assert session["audio"]["input"]["transcription"] == {
        "model": INPUT_TRANSCRIPTION_MODEL
    }
    assert session["audio"]["output"]["voice"] == OUTPUT_VOICE
    assert session["audio"]["output"]["voice"] == "marin"


def test_create_realtime_client_secret_mints_ek_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "issue_discussion_platform.realtime_secrets.EnvVarsContainer.get_env_var",
        _fake_openai_api_key,
    )

    captured: dict[str, Any] = {}

    def fake_create(
        *, session: dict[str, Any] | None = None, **_: Any
    ) -> _FakeClientSecretResponse:
        captured["session"] = session
        return _FakeClientSecretResponse(
            value="ek_test_secret_123",
            expires_at=1_700_000_000,
        )

    mock_client_secrets = MagicMock()
    mock_client_secrets.create.side_effect = fake_create
    mock_realtime = MagicMock()
    mock_realtime.client_secrets = mock_client_secrets
    mock_client = MagicMock(spec=OpenAI)
    mock_client.realtime = mock_realtime

    openai_calls: list[dict[str, str]] = []

    def fake_openai(*, api_key: str) -> MagicMock:
        openai_calls.append({"api_key": api_key})
        return mock_client

    monkeypatch.setattr(
        "issue_discussion_platform.realtime_secrets.OpenAI",
        fake_openai,
    )

    result = create_realtime_client_secret()

    assert result.value == "ek_test_secret_123"
    assert result.value.startswith("ek_")
    assert result.expires_at == 1_700_000_000
    assert openai_calls == [{"api_key": "sk-test-server-key"}]
    assert captured["session"] == build_realtime_session_config()
    mock_client_secrets.create.assert_called_once()
    assert CLIENT_SECRETS_PATH == "/realtime/client_secrets"


def test_create_realtime_client_secret_uses_injected_client() -> None:
    captured: dict[str, Any] = {}

    def fake_create(
        *, session: dict[str, Any] | None = None, **_: Any
    ) -> _FakeClientSecretResponse:
        captured["session"] = session
        return _FakeClientSecretResponse(value="ek_injected", expires_at=42)

    mock_client_secrets = MagicMock()
    mock_client_secrets.create.side_effect = fake_create
    mock_realtime = MagicMock()
    mock_realtime.client_secrets = mock_client_secrets
    mock_client = MagicMock(spec=OpenAI)
    mock_client.realtime = mock_realtime

    result = create_realtime_client_secret(client=mock_client)

    assert result.value == "ek_injected"
    assert result.expires_at == 42
    assert captured["session"]["model"] == "gpt-realtime-2.1"
    assert captured["session"]["instructions"] == SYSTEM_PROMPT


def test_create_realtime_client_secret_raises_on_api_error() -> None:
    def fake_create(**_: Any) -> _FakeClientSecretResponse:
        raise APIStatusError(
            "bad request",
            response=MagicMock(status_code=401),
            body={"error": {"message": "invalid api key"}},
        )

    mock_client_secrets = MagicMock()
    mock_client_secrets.create.side_effect = fake_create
    mock_realtime = MagicMock()
    mock_realtime.client_secrets = mock_client_secrets
    mock_client = MagicMock(spec=OpenAI)
    mock_client.realtime = mock_realtime

    with pytest.raises(RealtimeClientSecretError, match="status 401"):
        create_realtime_client_secret(client=mock_client)
