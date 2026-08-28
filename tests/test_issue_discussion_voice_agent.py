"""Tests for issue_discussion_platform voice_agent realtime slice."""

from __future__ import annotations

import asyncio
import inspect
import io
import wave

import numpy as np
import pytest
from agents.realtime.items import (
    AssistantAudio,
    AssistantMessageItem,
    InputAudio,
    UserMessageItem,
)
from agents.realtime.model_events import (
    RealtimeModelAudioEvent,
    RealtimeModelInputAudioTranscriptionCompletedEvent,
    RealtimeModelItemUpdatedEvent,
    RealtimeModelTurnEndedEvent,
    RealtimeModelTurnStartedEvent,
)
from agents.realtime.model_inputs import (
    RealtimeModelSendAudio,
    RealtimeModelSendRawMessage,
)
from agents.realtime.testing import RealtimeStep, ScriptedRealtimeModel

from issue_discussion_platform.voice_agent import (
    INPUT_TRANSCRIPTION_MODEL,
    OUTPUT_VOICE,
    REALTIME_MODEL,
    REALTIME_RUN_CONFIG,
    VoiceSession,
    pcm16_to_wav_bytes,
    wav_bytes_to_pcm16,
)


def _make_wav_bytes(
    samples: np.ndarray,
    sample_rate: int = 24000,
) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.astype(np.int16).tobytes())
    return buffer.getvalue()


def test_wav_pcm_helpers_round_trip() -> None:
    samples = np.array([0, 1000, -1000, 2000], dtype=np.int16)
    wav_bytes = pcm16_to_wav_bytes(samples, 24000)
    decoded, sample_rate = wav_bytes_to_pcm16(wav_bytes)
    assert sample_rate == 24000
    np.testing.assert_array_equal(decoded, samples)


@pytest.fixture
def mock_env_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def _scripted_model_for_turn(
    user_transcript: str,
    assistant_transcript: str,
    assistant_pcm: bytes,
) -> ScriptedRealtimeModel:
    user_item = UserMessageItem(
        item_id="user-item-1",
        content=[InputAudio(transcript=user_transcript)],
    )
    assistant_item = AssistantMessageItem(
        item_id="assistant-item-1",
        content=[AssistantAudio(transcript=assistant_transcript)],
    )
    return ScriptedRealtimeModel(
        steps=[
            RealtimeStep(
                expect=RealtimeModelSendAudio,
                emit=[
                    RealtimeModelInputAudioTranscriptionCompletedEvent(
                        item_id=user_item.item_id,
                        transcript=user_transcript,
                    ),
                    RealtimeModelItemUpdatedEvent(item=user_item),
                ],
            ),
            RealtimeStep(
                expect=lambda event: (
                    isinstance(event, RealtimeModelSendRawMessage)
                    and event.message.get("type") == "response.create"
                ),
                emit=[
                    RealtimeModelTurnStartedEvent(response_id="resp-1"),
                    RealtimeModelAudioEvent(
                        data=assistant_pcm,
                        response_id="resp-1",
                        item_id=assistant_item.item_id,
                        content_index=0,
                    ),
                    RealtimeModelItemUpdatedEvent(item=assistant_item),
                    RealtimeModelTurnEndedEvent(response_id="resp-1"),
                ],
            ),
        ],
    )


def test_handle_turn_returns_transcripts_and_reply_wav(
    mock_env_api_key: None,
) -> None:
    assistant_pcm = np.array([500, -500, 250], dtype=np.int16).tobytes()
    model = _scripted_model_for_turn(
        user_transcript="What should I focus on?",
        assistant_transcript="Tell me more about the issue.",
        assistant_pcm=assistant_pcm,
    )
    session = VoiceSession(instructions="Discuss the issue.", model=model)
    wav_bytes = _make_wav_bytes(np.zeros(2400, dtype=np.int16))

    result = asyncio.run(session.handle_turn(wav_bytes))

    assert result.user_text == "What should I focus on?"
    assert result.assistant_text == "Tell me more about the issue."
    reply_pcm, reply_rate = wav_bytes_to_pcm16(result.reply_wav_bytes)
    assert reply_rate == 24000
    np.testing.assert_array_equal(
        reply_pcm, np.frombuffer(assistant_pcm, dtype=np.int16)
    )
    model.assert_complete()


def test_realtime_run_config_uses_gpt_realtime_2_1() -> None:
    model_settings = REALTIME_RUN_CONFIG.get("model_settings")
    assert model_settings is not None
    assert model_settings.get("model_name") == "gpt-realtime-2.1"
    assert model_settings.get("reasoning") == {"effort": "low"}
    audio = model_settings.get("audio")
    assert audio is not None
    audio_input = audio.get("input")
    assert audio_input is not None
    assert audio_input.get("format") == "pcm16"
    assert audio_input.get("transcription") == {"model": INPUT_TRANSCRIPTION_MODEL}
    assert audio_input.get("turn_detection") is None
    assert audio.get("output") == {"format": "pcm16", "voice": OUTPUT_VOICE}


def test_voice_agent_module_has_no_legacy_voice_pipeline() -> None:
    import issue_discussion_platform.voice_agent as voice_agent

    source = inspect.getsource(voice_agent)
    assert "VoicePipeline" not in source
    assert "gpt-4.1-mini" not in source
    assert REALTIME_MODEL == "gpt-realtime-2.1"
