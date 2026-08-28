# WebRTC voice component (Slice B)

Streamlit **CCv2** custom component that connects the browser to OpenAI Realtime
via WebRTC (`RTCPeerConnection` + `oai-events` data channel).

## Manual test

1. Mint an ephemeral `ek_` client secret in Python (Slice C / `realtime_secrets`).
2. In a scratch Streamlit page:

   ```python
   from issue_discussion_platform.webrtc_voice import webrtc_voice

   secret = "ek_..."  # ephemeral, from server
   result = webrtc_voice(client_secret=secret, key="webrtc")
   st.write(result.connected, result.error)
   for line in result.transcripts:
       st.write(f"{line.role}: {line.text}")
   ```

3. Click **Connect**, allow microphone access, speak, and confirm you hear a
   streaming assistant reply (remote audio plays as it arrives; no WAV buffering).
4. Rerun the app (e.g. tweak another widget) and confirm the session stays
   connected when the component `key` is stable.

## Risks

- **Autoplay**: remote audio uses `<audio autoplay>`; the Connect click provides
  a user gesture, but some browsers may still block playback until interaction.
- **Mic permission**: `getUserMedia` requires HTTPS or localhost.
- **Streamlit reruns**: connection state is kept in a JS `WeakMap` and CCv2
  `setStateValue`; changing the component `key` remounts and drops the session.
- **Secret handling**: pass `ek_` only via `data.clientSecret`; do not store in
  `st.session_state` or log it.
