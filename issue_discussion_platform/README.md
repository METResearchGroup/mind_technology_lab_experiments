# Issue discussion platform

Streamlit experiment for talking through an issue with a **persistent WebRTC**
realtime voice agent. The browser connects directly to OpenAI **gpt-realtime-2.1**
using an ephemeral server-minted client secret; semantic VAD handles turn-taking
so you can speak naturally without push-to-talk record/stop.

## Run

From the repo root:

```bash
uv run streamlit run issue_discussion_platform/app.py
```

Use **localhost** or **HTTPS** so the browser can grant microphone permission.
Plain HTTP on a remote host will block mic access.

## Environment

Set `OPENAI_API_KEY` in the `.env` file at the repo root.

## How it works

1. Open the app; the server mints a short-lived `ek_` secret (kept in Streamlit
   session state only, never written to disk or `chat.jsonl`).
2. Click **Connect** in the WebRTC panel, allow the microphone, and speak.
3. Assistant audio plays in the browser as it arrives. Your speech is transcribed
   (`gpt-live-transcribe`) and both sides stream into chat as text arrives.
4. Session output (including `chat.jsonl`) is written under
   `issue_discussion_platform/outputs/`.

This is a browser WebRTC client (CCv2 component), not Streamlit push-to-talk.
