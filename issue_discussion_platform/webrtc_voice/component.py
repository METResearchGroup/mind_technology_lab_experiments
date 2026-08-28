"""Streamlit CCv2 WebRTC voice component for OpenAI Realtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import streamlit as st

from issue_discussion_platform.voice_agent import INPUT_TRANSCRIPTION_MODEL

_ASSET_DIR = Path(__file__).parent

_HTML = """
<div class="webrtc-voice">
  <audio id="wv-remote-audio" autoplay playsinline></audio>
  <div class="webrtc-voice__controls">
    <button id="wv-connect" type="button">Connect</button>
    <button id="wv-disconnect" type="button">Disconnect</button>
  </div>
  <p id="wv-status" class="webrtc-voice__status" aria-live="polite"></p>
</div>
"""

_CSS = """
.webrtc-voice {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  color: var(--st-text-color, inherit);
  font-family: var(--st-font-family, sans-serif);
}
.webrtc-voice__controls {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.webrtc-voice button {
  padding: 0.35rem 0.85rem;
  border-radius: var(--st-radius-medium, 0.5rem);
  border: 1px solid var(--st-border-color, #ccc);
  background: var(--st-secondary-background-color, #f0f2f6);
  color: var(--st-text-color, inherit);
  cursor: pointer;
  font: inherit;
}
.webrtc-voice button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.webrtc-voice button#wv-connect {
  background: var(--st-primary-color, #ff4b4b);
  color: var(--st-primary-color-text, #fff);
  border-color: transparent;
}
.webrtc-voice__status {
  margin: 0;
  font-size: 0.9rem;
  color: var(--st-text-color-secondary, #666);
}
#wv-remote-audio {
  display: none;
}
"""

_JS = (_ASSET_DIR / "frontend.js").read_text(encoding="utf-8")

_WEBRTC_VOICE = st.components.v2.component(
    "issue_discussion_webrtc_voice",
    html=_HTML,
    css=_CSS,
    js=_JS,
)

Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class TranscriptLine:
    """One transcript line from the realtime session."""

    role: Role
    text: str
    partial: bool = False


@dataclass(frozen=True)
class WebRTCVoiceResult:
    """Snapshot of component state returned to the Streamlit app."""

    connected: bool
    error: str | None
    transcripts: tuple[TranscriptLine, ...]


def _noop() -> None:
    return None


def _parse_transcripts(raw: Any) -> tuple[TranscriptLine, ...]:
    if not isinstance(raw, list):
        return ()
    lines: list[TranscriptLine] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        text = item.get("text")
        if role in ("user", "assistant") and isinstance(text, str) and text.strip():
            lines.append(
                TranscriptLine(
                    role=cast(Role, role),
                    text=text.strip() if not item.get("partial") else text,
                    partial=bool(item.get("partial")),
                )
            )
    return tuple(lines)


def webrtc_voice(
    client_secret: str | None = None,
    *,
    key: str = "webrtc",
    height: int = 120,
    on_connected_change: Callable[[], None] | None = None,
    on_error_change: Callable[[], None] | None = None,
    on_transcripts_change: Callable[[], None] | None = None,
) -> WebRTCVoiceResult:
    """Mount the WebRTC realtime voice component.

    Parameters
    ----------
    client_secret
        Ephemeral ``ek_`` secret minted server-side. Passed to the browser only
        for the SDP exchange; never persist in ``st.session_state``.
    key
        Stable Streamlit component key so connect state survives reruns.
    height
        Component frame height in pixels.
    on_connected_change, on_error_change, on_transcripts_change
        Optional CCv2 state callbacks (use ``lambda: None`` if you only need
        ``result`` attributes).

    Returns
    -------
    WebRTCVoiceResult
        ``connected``, ``error``, and accumulated ``transcripts`` (user +
        assistant) synced from the data channel via ``setStateValue``.
    """
    component_state = st.session_state.get(key, {})
    transcripts = component_state.get("transcripts", [])

    raw = _WEBRTC_VOICE(
        key=key,
        data={
            "clientSecret": client_secret or "",
            "connected": bool(component_state.get("connected", False)),
            "error": component_state.get("error"),
            "transcripts": transcripts,
            "transcriptionModel": INPUT_TRANSCRIPTION_MODEL,
        },
        default={
            "connected": False,
            "error": None,
            "transcripts": [],
        },
        on_connected_change=on_connected_change or _noop,
        on_error_change=on_error_change or _noop,
        on_transcripts_change=on_transcripts_change or _noop,
        height=height,
    )

    parsed = _parse_transcripts(raw.transcripts)
    return WebRTCVoiceResult(
        connected=bool(raw.connected),
        error=raw.error if isinstance(raw.error, str) else None,
        transcripts=parsed,
    )
