"""Voice session stubs for the issue discussion platform.

Run from the repo root:

    uv run streamlit run issue_discussion_platform/app.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt


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

    Raises
    ------
    NotImplementedError
        Stub implementation; filled in a later step.
    """
    raise NotImplementedError


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

    Raises
    ------
    NotImplementedError
        Stub implementation; filled in a later step.
    """
    raise NotImplementedError


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
    NotImplementedError
        Stub implementation; filled in a later step.
    """
    raise NotImplementedError


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

    Raises
    ------
    NotImplementedError
        Stub implementation; filled in a later step.
    """
    raise NotImplementedError


class VoiceSession:
    """Coordinates one voice discussion session with the OpenAI Agents voice API."""

    def __init__(self, instructions: str) -> None:
        """Configure a voice session with system instructions.

        Parameters
        ----------
        instructions
            System prompt text passed to the voice agent.
        """
        self._instructions = instructions

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
        NotImplementedError
            Stub implementation; filled in a later step.
        """
        raise NotImplementedError
