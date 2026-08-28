"""Voice session helpers for the issue discussion platform.

Run from the repo root:

    uv run streamlit run issue_discussion_platform/app.py
"""

from __future__ import annotations

import io
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt
from agents.realtime import RealtimeAgent, RealtimeRunner, RealtimeSession
from agents.realtime.config import RealtimeRunConfig
from agents.realtime.items import (
    AssistantMessageItem,
    RealtimeItem,
    UserMessageItem,
)
from agents.realtime.model import RealtimeModel
from agents.realtime.model_inputs import RealtimeModelSendRawMessage

from shared.load_env_vars import EnvVarsContainer

VOICE_SAMPLE_RATE_HZ = 24000
PCM_SAMPLE_WIDTH_BYTES = 2
MONO_CHANNEL_COUNT = 1
STEREO_CHANNEL_COUNT = 2
AGENT_NAME = "Issue discussion"
REALTIME_MODEL = "gpt-realtime-2.1"
INPUT_TRANSCRIPTION_MODEL = "gpt-live-transcribe"
OUTPUT_VOICE = "marin"

REALTIME_RUN_CONFIG: RealtimeRunConfig = {
    "model_settings": {
        "model_name": REALTIME_MODEL,
        "reasoning": {"effort": "low"},
        "audio": {
            "input": {
                "format": "pcm16",
                "transcription": {"model": INPUT_TRANSCRIPTION_MODEL},
                "turn_detection": None,
            },
            "output": {"format": "pcm16", "voice": OUTPUT_VOICE},
        },
    },
}


@dataclass(frozen=True)
class ChatLine:
    """One line in a session transcript."""

    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class TurnResult:
    """Outcome of one user audio turn and the assistant reply."""

    user_text: str
    assistant_text: str
    reply_wav_bytes: bytes


def create_session_dir(outputs_root: Path, timestamp: str) -> Path:
    """Create a timestamped directory for one discussion session.

    Parameters
    ----------
    outputs_root
        Parent directory that holds all session output folders.
    timestamp
        Unique session label, typically a formatted timestamp string.

    Returns
    -------
    Path
        Newly created session directory path.
    """
    session_dir = outputs_root / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def append_chat_lines(chat_path: Path, user_text: str, assistant_text: str) -> None:
    """Append one user and assistant exchange to a transcript file.

    Parameters
    ----------
    chat_path
        Path to the JSONL transcript file for the session.
    user_text
        Transcribed user utterance for this turn.
    assistant_text
        Assistant reply text for this turn.
    """
    chat_path.parent.mkdir(parents=True, exist_ok=True)
    with chat_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"role": "user", "content": user_text}) + "\n")
        handle.write(
            json.dumps({"role": "assistant", "content": assistant_text}) + "\n"
        )


def wav_bytes_to_pcm16(wav_bytes: bytes) -> tuple[npt.NDArray[np.int16], int]:
    """Decode WAV bytes to mono PCM16 samples and sample rate.

    Parameters
    ----------
    wav_bytes
        Raw WAV file contents.

    Returns
    -------
    tuple[npt.NDArray[np.int16], int]
        PCM16 sample array and sample rate in hertz.

    Raises
    ------
    ValueError
        If the WAV sample width is not 16-bit PCM.
    """
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        sample_width = wav_file.getsampwidth()
        if sample_width != PCM_SAMPLE_WIDTH_BYTES:
            raise ValueError(
                f"Expected {PCM_SAMPLE_WIDTH_BYTES}-byte PCM samples, "
                f"got sample width {sample_width} bytes."
            )
        num_channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    samples = np.frombuffer(frames, dtype=np.int16)
    if num_channels == STEREO_CHANNEL_COUNT:
        samples = samples.reshape(-1, STEREO_CHANNEL_COUNT)[:, 0]
    return samples, sample_rate


def pcm16_to_wav_bytes(pcm: npt.NDArray[np.int16], sample_rate: int) -> bytes:
    """Encode mono PCM16 samples as WAV bytes.

    Parameters
    ----------
    pcm
        Mono PCM16 sample array.
    sample_rate
        Sample rate in hertz for the encoded WAV.

    Returns
    -------
    bytes
        WAV file contents.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(MONO_CHANNEL_COUNT)
        wav_file.setsampwidth(PCM_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())
    return buffer.getvalue()


def _user_message_text(item: UserMessageItem) -> str:
    parts: list[str] = []
    for content in item.content:
        if content.type == "input_audio" and content.transcript:
            parts.append(content.transcript)
        elif content.type == "input_text" and content.text:
            parts.append(content.text)
    return " ".join(parts).strip()


def _assistant_message_text(item: AssistantMessageItem) -> str:
    parts: list[str] = []
    for content in item.content:
        if content.type == "audio" and content.transcript:
            parts.append(content.transcript)
        elif content.type == "text" and content.text:
            parts.append(content.text)
    return " ".join(parts).strip()


def _latest_transcripts_from_history(history: list[RealtimeItem]) -> tuple[str, str]:
    user_text = ""
    assistant_text = ""
    for item in history:
        if item.type != "message":
            continue
        if item.role == "user":
            text = _user_message_text(item)
            if text:
                user_text = text
        elif item.role == "assistant":
            text = _assistant_message_text(item)
            if text:
                assistant_text = text
    return user_text, assistant_text


def _instructions_with_history(
    base_instructions: str,
    turn_history: list[ChatLine],
) -> str:
    if not turn_history:
        return base_instructions
    lines = ["# Conversation so far", ""]
    for turn in turn_history:
        label = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{label}: {turn.content}")
    return base_instructions + "\n\n" + "\n".join(lines)


class VoiceSession:
    """Coordinates one voice discussion session over the OpenAI Realtime API.

    Each ``handle_turn`` opens a short-lived WebSocket session (Streamlit calls
    ``asyncio.run`` per turn, so a persistent socket cannot survive across turns).
    Prior transcript turns are replayed into the agent instructions so multi-turn
    memory is preserved without a long-lived connection.
    """

    def __init__(
        self,
        instructions: str,
        *,
        model: RealtimeModel | None = None,
    ) -> None:
        """Configure a voice session with system instructions.

        Parameters
        ----------
        instructions
            System prompt text passed to the realtime agent.
        model
            Optional realtime transport for tests. Production uses the default
            OpenAI WebSocket model.

        Raises
        ------
        ValueError
            If ``OPENAI_API_KEY`` is missing or empty.
        """
        EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
        self._instructions = instructions
        self._turn_history: list[ChatLine] = []
        self._model = model

    async def handle_turn(self, wav_bytes: bytes) -> TurnResult:
        """Process one user audio turn and return the assistant reply.

        Parameters
        ----------
        wav_bytes
            User utterance audio as WAV bytes.

        Returns
        -------
        TurnResult
            Transcripts and assistant reply audio for this turn.

        Raises
        ------
        ValueError
            If ``OPENAI_API_KEY`` is missing or empty, or the WAV sample rate
            is not 24000 Hz.
        RuntimeError
            If the realtime session reports an error event.
        """
        api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
        pcm, sample_rate = wav_bytes_to_pcm16(wav_bytes)
        if sample_rate != VOICE_SAMPLE_RATE_HZ:
            raise ValueError(
                f"Expected sample rate {VOICE_SAMPLE_RATE_HZ} Hz, "
                f"got {sample_rate} Hz. "
                "Record audio at 24000 Hz."
            )

        pcm_bytes = np.ascontiguousarray(pcm).tobytes()
        agent = RealtimeAgent(
            name=AGENT_NAME,
            instructions=_instructions_with_history(
                self._instructions,
                self._turn_history,
            ),
        )
        runner = RealtimeRunner(
            starting_agent=agent,
            config=REALTIME_RUN_CONFIG,
            model=self._model,
        )

        user_text = ""
        assistant_text = ""
        audio_chunks: list[bytes] = []

        async with await runner.run(model_config={"api_key": api_key}) as session:
            await session.send_audio(pcm_bytes, commit=True)
            await _request_assistant_response(session)

            async for event in session:
                if event.type == "audio":
                    audio_chunks.append(event.audio.data)
                elif event.type == "history_added":
                    if event.item.type == "message" and event.item.role == "user":
                        user_text = _user_message_text(event.item) or user_text
                    elif (
                        event.item.type == "message" and event.item.role == "assistant"
                    ):
                        assistant_text = (
                            _assistant_message_text(event.item) or assistant_text
                        )
                elif event.type == "history_updated":
                    updated_user, updated_assistant = _latest_transcripts_from_history(
                        event.history,
                    )
                    if updated_user:
                        user_text = updated_user
                    if updated_assistant:
                        assistant_text = updated_assistant
                elif event.type == "agent_end":
                    break
                elif event.type == "error":
                    raise RuntimeError(f"Realtime session error: {event.error}")

        if audio_chunks:
            reply_pcm = np.frombuffer(b"".join(audio_chunks), dtype=np.int16)
        else:
            reply_pcm = np.array([], dtype=np.int16)

        reply_wav_bytes = pcm16_to_wav_bytes(reply_pcm, VOICE_SAMPLE_RATE_HZ)
        self._turn_history.append(ChatLine(role="user", content=user_text))
        self._turn_history.append(
            ChatLine(role="assistant", content=assistant_text),
        )
        return TurnResult(
            user_text=user_text,
            assistant_text=assistant_text,
            reply_wav_bytes=reply_wav_bytes,
        )


async def _request_assistant_response(session: RealtimeSession) -> None:
    """Start model inference after a committed push-to-talk audio clip."""
    await session.model.send_event(
        RealtimeModelSendRawMessage(message={"type": "response.create"}),
    )
