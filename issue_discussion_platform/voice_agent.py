"""Voice session helpers for the issue discussion platform.

Run from the repo root:

    uv run streamlit run issue_discussion_platform/app.py
"""

from __future__ import annotations

import io
import json
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt
from agents import Agent
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    VoicePipeline,
    VoiceWorkflowBase,
)

from shared.load_env_vars import EnvVarsContainer

VOICE_SAMPLE_RATE_HZ = 24000
PCM_SAMPLE_WIDTH_BYTES = 2
MONO_CHANNEL_COUNT = 1
STEREO_CHANNEL_COUNT = 2
AGENT_NAME = "Issue discussion"
AGENT_MODEL = "gpt-4.1-mini"
VOICE_STREAM_EVENT_AUDIO = "voice_stream_event_audio"


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


class CapturingVoiceWorkflow(VoiceWorkflowBase):
    """Delegates to an inner workflow and captures per-turn transcript text.

    After each ``run`` call, ``last_user_text`` holds the user transcription and
    ``last_assistant_text`` holds the full assistant reply for that turn.
    """

    def __init__(self, inner: SingleAgentVoiceWorkflow) -> None:
        self._inner = inner
        self.last_user_text = ""
        self.last_assistant_text = ""

    async def run(self, transcription: str) -> AsyncIterator[str]:
        """Run the inner workflow and capture transcript text for the turn.

        Parameters
        ----------
        transcription
            Speech-to-text output for the user's audio clip.

        Yields
        ------
        str
            Assistant text chunks passed through to text-to-speech.
        """
        self.last_user_text = transcription
        assistant_chunks: list[str] = []
        async for chunk in self._inner.run(transcription):
            assistant_chunks.append(chunk)
            yield chunk
        self.last_assistant_text = "".join(assistant_chunks)


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


class VoiceSession:
    """Coordinates one voice discussion session with the OpenAI Agents voice API.

    Keeps conversation history across turns via a single voice pipeline instance.
    """

    def __init__(self, instructions: str) -> None:
        """Configure a voice session with system instructions.

        Parameters
        ----------
        instructions
            System prompt text passed to the voice agent.

        Raises
        ------
        ValueError
            If ``OPENAI_API_KEY`` is missing or empty.
        """
        EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
        agent = Agent(
            name=AGENT_NAME,
            instructions=instructions,
            model=AGENT_MODEL,
        )
        inner_workflow = SingleAgentVoiceWorkflow(agent)
        self._workflow = CapturingVoiceWorkflow(inner_workflow)
        self._pipeline = VoicePipeline(workflow=self._workflow)

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
        """
        EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
        pcm, sample_rate = wav_bytes_to_pcm16(wav_bytes)
        if sample_rate != VOICE_SAMPLE_RATE_HZ:
            raise ValueError(
                f"Expected sample rate {VOICE_SAMPLE_RATE_HZ} Hz, "
                f"got {sample_rate} Hz. "
                "Record audio at 24000 Hz."
            )

        audio_input = AudioInput(buffer=pcm, frame_rate=VOICE_SAMPLE_RATE_HZ)
        result = await self._pipeline.run(audio_input)

        audio_chunks: list[npt.NDArray[np.int16]] = []
        async for event in result.stream():
            if event.type == VOICE_STREAM_EVENT_AUDIO and event.data is not None:
                audio_chunks.append(event.data.reshape(-1).astype(np.int16))

        if audio_chunks:
            reply_pcm = np.concatenate(audio_chunks).astype(np.int16)
        else:
            reply_pcm = np.array([], dtype=np.int16)

        reply_wav_bytes = pcm16_to_wav_bytes(reply_pcm, VOICE_SAMPLE_RATE_HZ)
        return TurnResult(
            user_text=self._workflow.last_user_text,
            assistant_text=self._workflow.last_assistant_text,
            reply_wav_bytes=reply_wav_bytes,
        )
