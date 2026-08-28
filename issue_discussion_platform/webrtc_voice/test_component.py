"""Unit tests for the WebRTC voice Python wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from unittest.mock import MagicMock, patch

import pytest

from issue_discussion_platform.voice_agent import INPUT_TRANSCRIPTION_MODEL
from issue_discussion_platform.webrtc_voice.component import (
    TranscriptLine,
    WebRTCVoiceResult,
    _parse_transcripts,
    webrtc_voice,
)


def _assistant_transcript_from_response(response: dict[str, Any]) -> str:
    """Mirror of frontend.js assistantTranscriptFromResponse."""
    parts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "audio" and isinstance(part.get("transcript"), str):
                parts.append(part["transcript"])
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                parts.append(part["text"])
    return "".join(parts).strip()


def _simulate_assistant_transcript_events(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mirror of frontend.js assistant transcript aggregation.

    One bubble per response.done.
    """
    transcripts: list[dict[str, Any]] = []
    active_response_id: str | None = None
    delta_stream: Literal["legacy", "ga"] | None = None
    completed_response_ids: set[str] = set()

    def apply_delta(delta: str) -> None:
        if not delta:
            return
        last = transcripts[-1] if transcripts else None
        if last and last.get("role") == "assistant" and last.get("partial"):
            last["text"] += delta
        else:
            transcripts.append({"role": "assistant", "text": delta, "partial": True})

    def finalize(text: str) -> None:
        trimmed = text.strip()
        if not trimmed:
            return
        if transcripts and transcripts[-1].get("role") == "assistant":
            transcripts[-1]["text"] = trimmed
            transcripts[-1]["partial"] = False
        else:
            transcripts.append({"role": "assistant", "text": trimmed, "partial": False})

    def response_id_from_event(msg: dict[str, Any]) -> str | None:
        if isinstance(msg.get("response_id"), str):
            return msg["response_id"]
        response = msg.get("response")
        if isinstance(response, dict) and isinstance(response.get("id"), str):
            return response["id"]
        return None

    def should_apply_delta(msg_type: str, response_id: str | None) -> bool:
        nonlocal active_response_id, delta_stream
        if not response_id:
            return True
        if response_id in completed_response_ids:
            return False
        if active_response_id is None:
            active_response_id = response_id
            delta_stream = None
        elif active_response_id != response_id:
            return False

        stream = (
            "legacy"
            if msg_type == "response.audio_transcript.delta"
            else "ga"
            if msg_type == "response.output_audio_transcript.delta"
            else None
        )
        if stream is None:
            return True
        if delta_stream is None:
            delta_stream = stream
            return True
        return delta_stream == stream

    for msg in events:
        msg_type = msg.get("type")
        if msg_type in (
            "response.audio_transcript.delta",
            "response.output_audio_transcript.delta",
        ):
            response_id = response_id_from_event(msg)
            delta = msg.get("delta")
            if isinstance(delta, str) and should_apply_delta(msg_type, response_id):
                apply_delta(delta)
            continue

        if msg_type in (
            "response.audio_transcript.done",
            "response.output_audio_transcript.done",
        ):
            continue

        if msg_type == "response.done":
            response = msg.get("response")
            response_id = response_id_from_event(msg)
            if isinstance(response, dict):
                transcript = _assistant_transcript_from_response(response)
                if not transcript and transcripts and transcripts[-1].get("partial"):
                    transcript = str(transcripts[-1].get("text", "")).strip()
                if transcript:
                    finalize(transcript)
            if response_id:
                completed_response_ids.add(response_id)
            if active_response_id == response_id:
                active_response_id = None
                delta_stream = None

    return transcripts


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


def test_frontend_does_not_finalize_assistant_on_part_done() -> None:
    frontend = (Path(__file__).resolve().parent / "frontend.js").read_text(
        encoding="utf-8"
    )
    after_part_done = frontend.split("response.output_audio_transcript.done")[1]
    part_done_handler = after_part_done.split('if (type === "response.done")')[0]
    assert "finalizeTranscript" not in part_done_handler
    assert "assistantTranscriptFromResponse" in frontend
    assert "completeAssistantResponse" in frontend


class TestAssistantTranscriptAggregation:
    def test_one_bubble_across_part_done_and_response_done(self) -> None:
        events = [
            {
                "type": "response.output_audio_transcript.delta",
                "response_id": "resp_1",
                "delta": "Hello, I hear you. ",
            },
            {
                "type": "response.output_audio_transcript.done",
                "response_id": "resp_1",
                "transcript": "Hello, I hear you. ",
            },
            {
                "type": "response.output_audio_transcript.delta",
                "response_id": "resp_1",
                "delta": "What feels most important right now?",
            },
            {
                "type": "response.done",
                "response": {
                    "id": "resp_1",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "audio",
                                    "transcript": (
                                        "Hello, I hear you. "
                                        "What feels most important right now?"
                                    ),
                                }
                            ],
                        }
                    ],
                },
            },
        ]

        transcripts = _simulate_assistant_transcript_events(events)
        assistant_lines = [line for line in transcripts if line["role"] == "assistant"]

        assert len(assistant_lines) == 1
        assert assistant_lines[0]["partial"] is False
        assert assistant_lines[0]["text"] == (
            "Hello, I hear you. What feels most important right now?"
        )

    def test_deduplicates_legacy_and_ga_delta_streams(self) -> None:
        events = [
            {
                "type": "response.audio_transcript.delta",
                "response_id": "resp_2",
                "delta": "Same ",
            },
            {
                "type": "response.output_audio_transcript.delta",
                "response_id": "resp_2",
                "delta": "Same ",
            },
            {
                "type": "response.done",
                "response": {
                    "id": "resp_2",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "audio", "transcript": "Same text"}],
                        }
                    ],
                },
            },
        ]

        transcripts = _simulate_assistant_transcript_events(events)
        assistant_lines = [line for line in transcripts if line["role"] == "assistant"]

        assert len(assistant_lines) == 1
        assert assistant_lines[0]["text"] == "Same text"
