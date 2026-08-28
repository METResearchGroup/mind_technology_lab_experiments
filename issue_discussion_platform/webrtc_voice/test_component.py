"""Unit tests for the WebRTC voice Python wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from issue_discussion_platform.voice_agent import INPUT_TRANSCRIPTION_MODEL
from issue_discussion_platform.webrtc_voice.component import (
    TranscriptLine,
    WebRTCVoiceResult,
    _parse_transcripts,
    webrtc_voice,
)


class TestParseTranscripts:
    def test_empty_and_invalid(self) -> None:
        assert _parse_transcripts(None) == ()
        assert _parse_transcripts("nope") == ()
        assert _parse_transcripts([{"role": "user"}]) == ()

    def test_valid_lines(self) -> None:
        raw = [
            {"role": "user", "text": " hello "},
            {"role": "assistant", "text": "Hi there"},
            {"role": "system", "text": "ignored"},
        ]
        assert _parse_transcripts(raw) == (
            TranscriptLine(role="user", text="hello"),
            TranscriptLine(role="assistant", text="Hi there"),
        )

    def test_partial_line(self) -> None:
        raw = [{"role": "assistant", "text": "Hello ", "partial": True}]
        assert _parse_transcripts(raw) == (
            TranscriptLine(role="assistant", text="Hello ", partial=True),
        )


_PATCH_SESSION = patch(
    "issue_discussion_platform.webrtc_voice.component.st.session_state",
    new_callable=dict,
)


@patch("issue_discussion_platform.webrtc_voice.component._WEBRTC_VOICE")
@_PATCH_SESSION
def test_webrtc_voice_mounts_with_secret(
    mock_session_state: dict[str, object],
    mock_mount: MagicMock,
) -> None:
    mock_mount.return_value = MagicMock(
        connected=True,
        error=None,
        transcripts=[{"role": "user", "text": "test"}],
    )

    result = webrtc_voice("ek_test_secret_123", key="voice-key")

    mock_mount.assert_called_once()
    kwargs = mock_mount.call_args.kwargs
    assert kwargs["key"] == "voice-key"
    assert kwargs["data"]["clientSecret"] == "ek_test_secret_123"
    assert kwargs["data"]["transcriptionModel"] == INPUT_TRANSCRIPTION_MODEL
    assert kwargs["height"] == 120
    assert kwargs["default"] == {
        "connected": False,
        "error": None,
        "transcripts": [],
    }

    assert isinstance(result, WebRTCVoiceResult)
    assert result.connected is True
    assert result.error is None
    assert result.transcripts == (TranscriptLine(role="user", text="test"),)


@patch("issue_discussion_platform.webrtc_voice.component._WEBRTC_VOICE")
@_PATCH_SESSION
def test_webrtc_voice_reads_existing_session_state(
    mock_session_state: dict[str, object],
    mock_mount: MagicMock,
) -> None:
    mock_session_state["webrtc"] = {
        "connected": True,
        "transcripts": [{"role": "assistant", "text": "prior"}],
    }
    mock_mount.return_value = MagicMock(connected=True, error=None, transcripts=[])

    webrtc_voice(client_secret="ek_abc", key="webrtc")

    data = mock_mount.call_args.kwargs["data"]
    assert data["connected"] is True
    assert data["transcripts"] == [{"role": "assistant", "text": "prior"}]


@pytest.mark.parametrize(
    ("error_value", "expected"),
    [
        ("mic denied", "mic denied"),
        (None, None),
        (123, None),
    ],
)
@patch("issue_discussion_platform.webrtc_voice.component._WEBRTC_VOICE")
@_PATCH_SESSION
def test_webrtc_voice_error_typing(
    mock_session_state: dict[str, object],
    mock_mount: MagicMock,
    error_value: object,
    expected: str | None,
) -> None:
    mock_mount.return_value = MagicMock(
        connected=False,
        error=error_value,
        transcripts=[],
    )

    result = webrtc_voice(key="k")
    assert result.error == expected


def test_frontend_enables_user_input_transcription() -> None:
    frontend = (Path(__file__).resolve().parent / "frontend.js").read_text(
        encoding="utf-8"
    )
    assert "session.update" in frontend
    assert "conversation.item.input_audio_transcription.completed" in frontend
    assert "conversation.item.input_audio_transcription.delta" in frontend
    assert "response.output_audio_transcript.delta" in frontend
    assert "applyTranscriptDelta" in frontend
    assert "transcription: { model: transcriptionModel }" in frontend
