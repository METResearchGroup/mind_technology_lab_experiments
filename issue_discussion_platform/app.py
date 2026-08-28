"""Streamlit entrypoint for the issue discussion voice experiment.

Run from the repo root:

    uv run streamlit run issue_discussion_platform/app.py
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path

import streamlit as st

from issue_discussion_platform.prompts import SYSTEM_PROMPT
from issue_discussion_platform.voice_agent import (
    VoiceSession,
    append_chat_lines,
    create_session_dir,
)
from shared.load_env_vars import EnvVarsContainer

AUDIO_SAMPLE_RATE = 24000
AUDIO_WAV_MIME = "audio/wav"
AUDIO_INPUT_LABEL = "Record a turn"
HASH_ALGORITHM = "sha256"
OUTPUTS_ROOT = Path("issue_discussion_platform/outputs")
PAGE_TITLE = "Issue discussion"
RECORDING_INSTRUCTION = "Click the microphone, speak your turn, then stop recording."
SESSION_DIR_KEY = "session_dir"
VOICE_SESSION_KEY = "voice_session"
MESSAGES_KEY = "messages"
LAST_AUDIO_FINGERPRINT_KEY = "last_audio_fingerprint"
LAST_REPLY_WAV_KEY = "last_reply_wav"
SESSION_INITIALIZED_KEY = "session_initialized"
OPENAI_API_KEY_NAME = "OPENAI_API_KEY"
CHAT_FILENAME = "chat.jsonl"
EMPTY_MESSAGES: list[dict[str, str]] = []


def _ensure_session_state() -> None:
    """Create per-browser session folders and voice state on first load."""
    if st.session_state.get(SESSION_INITIALIZED_KEY):
        return

    EnvVarsContainer.get_env_var(OPENAI_API_KEY_NAME, required=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state[SESSION_DIR_KEY] = create_session_dir(OUTPUTS_ROOT, timestamp)
    st.session_state[VOICE_SESSION_KEY] = VoiceSession(instructions=SYSTEM_PROMPT)
    st.session_state[MESSAGES_KEY] = list(EMPTY_MESSAGES)
    st.session_state[LAST_AUDIO_FINGERPRINT_KEY] = None
    st.session_state[LAST_REPLY_WAV_KEY] = None
    st.session_state[SESSION_INITIALIZED_KEY] = True


def _fingerprint_audio(wav_bytes: bytes) -> str:
    """Return a stable hash for recorded audio bytes.

    Parameters
    ----------
    wav_bytes
        Raw WAV file contents from the microphone widget.

    Returns
    -------
    str
        Hex digest used to skip duplicate Streamlit reruns.
    """
    digest = hashlib.new(HASH_ALGORITHM)
    digest.update(wav_bytes)
    return digest.hexdigest()


def _handle_new_recording(wav_bytes: bytes, fingerprint: str) -> None:
    """Run one voice turn and persist transcript lines when audio is new.

    Parameters
    ----------
    wav_bytes
        Recorded WAV bytes from ``st.audio_input``.
    fingerprint
        SHA-256 hex digest of ``wav_bytes``.
    """
    if fingerprint == st.session_state.get(LAST_AUDIO_FINGERPRINT_KEY):
        return

    voice_session: VoiceSession = st.session_state[VOICE_SESSION_KEY]
    try:
        result = asyncio.run(voice_session.handle_turn(wav_bytes))
    except ValueError as exc:
        st.error(str(exc))
        return

    messages: list[dict[str, str]] = st.session_state[MESSAGES_KEY]
    messages.append({"role": "user", "content": result.user_text})
    messages.append({"role": "assistant", "content": result.assistant_text})
    session_dir: Path = st.session_state[SESSION_DIR_KEY]
    append_chat_lines(
        session_dir / CHAT_FILENAME, result.user_text, result.assistant_text
    )
    st.session_state[LAST_REPLY_WAV_KEY] = result.reply_wav_bytes
    st.session_state[LAST_AUDIO_FINGERPRINT_KEY] = fingerprint


def _render_messages(messages: list[dict[str, str]]) -> None:
    """Show the transcript in chat order.

    Parameters
    ----------
    messages
        Ordered user and assistant message dicts with ``role`` and ``content``.
    """
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


def _render_reply_audio(last_reply_wav: bytes | None) -> None:
    """Play the latest assistant reply when available.

    Parameters
    ----------
    last_reply_wav
        WAV bytes for the most recent assistant reply, if any.
    """
    if last_reply_wav is None:
        return
    st.audio(last_reply_wav, format=AUDIO_WAV_MIME, autoplay=True)


def main() -> None:
    """Render the issue discussion microphone page."""
    try:
        _ensure_session_state()
    except ValueError as exc:
        st.error(str(exc))
        return

    st.title(PAGE_TITLE)
    st.write(RECORDING_INSTRUCTION)

    recording = st.audio_input(AUDIO_INPUT_LABEL, sample_rate=AUDIO_SAMPLE_RATE)
    if recording is not None:
        wav_bytes = recording.getvalue()
        _handle_new_recording(wav_bytes, _fingerprint_audio(wav_bytes))

    messages: list[dict[str, str]] = st.session_state.get(MESSAGES_KEY, EMPTY_MESSAGES)
    _render_messages(messages)
    _render_reply_audio(st.session_state.get(LAST_REPLY_WAV_KEY))


main()
