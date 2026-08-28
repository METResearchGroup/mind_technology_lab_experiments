# Issue discussion platform

Streamlit push-to-talk experiment for talking through an issue with a realtime
voice agent. Each turn sends recorded audio to OpenAI **gpt-realtime-2.1**
(speech-to-speech over a short-lived WebSocket session). The app replays prior
turns in the agent instructions so multi-turn memory works without keeping a
socket open across Streamlit reruns.

## Run

From the repo root:

```bash
uv run streamlit run issue_discussion_platform/app.py
```

## Environment

Set `OPENAI_API_KEY` in the `.env` file at the repo root.

## Audio

Record at **24 kHz** mono (the microphone widget is configured for 24000 Hz).
Assistant replies are returned as 24 kHz WAV and autoplay after each turn.

## How it works

1. Click the microphone, speak one turn, then stop recording.
2. The app sends that clip to the realtime model and shows user and assistant
   transcripts in the chat (empty transcripts are skipped).
3. Session output (including `chat.jsonl`) is written under
   `issue_discussion_platform/outputs/`.

This is a Streamlit push-to-talk UI, not a browser WebRTC client.
