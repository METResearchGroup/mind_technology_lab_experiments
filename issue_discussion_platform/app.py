"""Streamlit entrypoint for the issue discussion voice experiment.

Run from the repo root:

    uv run streamlit run issue_discussion_platform/app.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from issue_discussion_platform.realtime_secrets import (
    RealtimeClientSecretError,
    create_realtime_client_secret,
)
from issue_discussion_platform.voice_agent import (
    REALTIME_MODEL,
    append_chat_lines,
    create_session_dir,
)
from issue_discussion_platform.webrtc_voice import TranscriptLine, webrtc_voice
from shared.load_env_vars import EnvVarsContainer

OUTPUTS_ROOT = Path("issue_discussion_platform/outputs")
PAGE_TITLE = "Issue discussion"
REALTIME_CAPTION = (
    f"Realtime voice agent ({REALTIME_MODEL}). Persistent WebRTC with semantic VAD—"
    "speak naturally; no record/stop clip."
)
SESSION_DIR_KEY = "session_dir"
SESSION_INITIALIZED_KEY = "session_initialized"
REALTIME_SECRET_KEY = "realtime_client_secret"
PERSISTED_TRANSCRIPT_COUNT_KEY = "persisted_transcript_count"
OPENAI_API_KEY_NAME = "OPENAI_API_KEY"
CHAT_FILENAME = "chat.jsonl"
WEBRTC_COMPONENT_KEY = "webrtc"


def _ensure_session_state() -> None:
    """Create per-browser session folders on first load."""
    if st.session_state.get(SESSION_INITIALIZED_KEY):
        return

    EnvVarsContainer.get_env_var(OPENAI_API_KEY_NAME, required=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state[SESSION_DIR_KEY] = create_session_dir(OUTPUTS_ROOT, timestamp)
    st.session_state[PERSISTED_TRANSCRIPT_COUNT_KEY] = 0
    st.session_state[SESSION_INITIALIZED_KEY] = True


def _secret_is_valid(secret_state: dict[str, object] | None) -> bool:
    """Return whether a cached client secret is still usable."""
    if not secret_state:
        return False
    value = secret_state.get("value")
    expires_at = secret_state.get("expires_at")
    if not isinstance(value, str) or not value:
        return False
    if not isinstance(expires_at, int):
        return False
    now = int(datetime.now(UTC).timestamp())
    return expires_at > now


def _mint_client_secret() -> str:
    """Mint or refresh the ephemeral Realtime client secret in session state."""
    secret = create_realtime_client_secret()
    st.session_state[REALTIME_SECRET_KEY] = {
        "value": secret.value,
        "expires_at": secret.expires_at,
    }
    return secret.value


def _get_client_secret() -> str | None:
    """Return a valid ephemeral secret, minting when missing or expired."""
    secret_state = st.session_state.get(REALTIME_SECRET_KEY)
    if _secret_is_valid(secret_state):
        return str(secret_state["value"])
    try:
        return _mint_client_secret()
    except RealtimeClientSecretError as exc:
        st.session_state.pop(REALTIME_SECRET_KEY, None)
        st.error(str(exc))
        return None


def _persist_new_transcripts(
    chat_path: Path,
    transcripts: tuple[TranscriptLine, ...],
    persisted_count: int,
) -> int:
    """Append transcript lines not yet written to ``chat.jsonl``.

    Pairs consecutive user/assistant lines via ``append_chat_lines``. Unpaired
    lines are flushed individually so nothing is dropped when turn order varies.
    """
    index = persisted_count
    while index < len(transcripts):
        line = transcripts[index]
        if line.partial:
            break
        if line.role == "user":
            if index + 1 < len(transcripts):
                assistant_line = transcripts[index + 1]
                if assistant_line.partial:
                    break
                if assistant_line.role == "assistant":
                    append_chat_lines(chat_path, line.text, assistant_line.text)
                    index += 2
                    continue
            append_chat_lines(chat_path, line.text, "")
            index += 1
        elif line.role == "assistant":
            append_chat_lines(chat_path, "", line.text)
            index += 1
        else:
            index += 1
    return index


def _sync_transcript_persistence(transcripts: tuple[TranscriptLine, ...]) -> None:
    """Persist any new transcript lines from the WebRTC component."""
    persisted_count = int(st.session_state.get(PERSISTED_TRANSCRIPT_COUNT_KEY, 0))
    if persisted_count >= len(transcripts):
        return

    session_dir: Path = st.session_state[SESSION_DIR_KEY]
    new_count = _persist_new_transcripts(
        session_dir / CHAT_FILENAME,
        transcripts,
        persisted_count,
    )
    st.session_state[PERSISTED_TRANSCRIPT_COUNT_KEY] = new_count


def _render_transcripts(transcripts: tuple[TranscriptLine, ...]) -> None:
    """Show live transcript lines as chat messages."""
    for line in transcripts:
        with st.chat_message(line.role):
            st.write(line.text if not line.partial else f"{line.text}▌")


def _render_connection_status(connected: bool, error: str | None) -> None:
    """Show WebRTC connect state or the latest component error."""
    if error:
        st.error(error)
    elif connected:
        st.success("Connected — speak naturally; the assistant replies with voice.")


def main() -> None:
    """Render the issue discussion WebRTC voice page."""
    try:
        _ensure_session_state()
    except ValueError as exc:
        st.error(str(exc))
        return

    st.title(PAGE_TITLE)
    st.caption(REALTIME_CAPTION)

    client_secret = _get_client_secret()
    if client_secret is None:
        return

    result = webrtc_voice(client_secret=client_secret, key=WEBRTC_COMPONENT_KEY)
    _sync_transcript_persistence(result.transcripts)
    _render_connection_status(result.connected, result.error)
    _render_transcripts(result.transcripts)


main()
