"""Mint ephemeral OpenAI Realtime client secrets for browser WebRTC.

The server API key never leaves this process; browsers receive only a short-lived
``ek_`` token for WebRTC session setup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import APIStatusError, OpenAI

from issue_discussion_platform.prompts import SYSTEM_PROMPT
from issue_discussion_platform.voice_agent import (
    INPUT_TRANSCRIPTION_MODEL,
    OUTPUT_VOICE,
    REALTIME_MODEL,
)
from shared.load_env_vars import EnvVarsContainer

CLIENT_SECRETS_PATH = "/realtime/client_secrets"


class RealtimeClientSecretError(RuntimeError):
    """Failed to mint an ephemeral Realtime client secret."""


@dataclass(frozen=True)
class RealtimeClientSecret:
    """Short-lived client secret for browser Realtime WebRTC connections."""

    value: str
    expires_at: int


def build_realtime_session_config() -> dict[str, Any]:
    """Return the session object sent when minting a client secret."""
    return {
        "type": "realtime",
        "model": REALTIME_MODEL,
        "reasoning": {"effort": "low"},
        "instructions": SYSTEM_PROMPT,
        "audio": {
            "input": {
                "turn_detection": {"type": "semantic_vad"},
                "transcription": {"model": INPUT_TRANSCRIPTION_MODEL},
            },
            "output": {"voice": OUTPUT_VOICE},
        },
    }


def create_realtime_client_secret(
    *,
    client: OpenAI | None = None,
) -> RealtimeClientSecret:
    """Mint an ephemeral ``ek_`` client secret for browser Realtime WebRTC.

    Parameters
    ----------
    client
        Optional OpenAI client for tests. Production callers omit this; the
        server API key is read from ``OPENAI_API_KEY``.

    Returns
    -------
    RealtimeClientSecret
        Parsed secret value and expiration timestamp.

    Raises
    ------
    RealtimeClientSecretError
        If the OpenAI API returns a non-success response.
    ValueError
        If ``OPENAI_API_KEY`` is missing or empty.
    """
    openai_client = client or OpenAI(
        api_key=EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True),
    )

    try:
        response = openai_client.realtime.client_secrets.create(
            session=build_realtime_session_config(),
        )
    except APIStatusError as exc:
        raise RealtimeClientSecretError(
            "OpenAI client secret request failed with status "
            f"{exc.status_code}: {exc.message}"
        ) from exc

    return RealtimeClientSecret(
        value=response.value,
        expires_at=response.expires_at,
    )
