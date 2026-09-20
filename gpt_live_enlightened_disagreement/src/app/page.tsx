"use client";

import { useRef, useState } from "react";
import {
  CONNECTED_STATUS,
  CONNECTING_STATUS,
  startLiveCall,
  stopLiveCall,
} from "@/lib/live-webrtc";
import type { CaptionState } from "@/lib/live-captions";

const IDLE_STATUS = "Idle";
const PAGE_HEADING = "GPT-Live debate";
const ROLE_LINE =
  "You argue for socialism. The agent is a capitalist devil's advocate.";
const COST_NOTE =
  "Voice is billed at $0.05 per minute. Grant the microphone only if you accept that charge. The OpenAI key stays on the server.";
const YOU_LABEL = "You";
const AGENT_LABEL = "Agent";
const EMPTY_CAPTIONS: CaptionState = { user: "", assistant: "" };

async function fetchSession(sdp: string): Promise<Response> {
  return fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sdp }),
  });
}

function requestMicrophone(
  constraints: MediaStreamConstraints,
): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia(constraints);
}

function playRemoteTrack(
  audio: HTMLAudioElement | null,
  track: MediaStreamTrack,
): void {
  if (!audio) {
    return;
  }
  audio.srcObject = new MediaStream([track]);
  void audio.play();
}

function statusFromError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default function Home() {
  const [status, setStatus] = useState(IDLE_STATUS);
  const [captions, setCaptions] = useState<CaptionState>(EMPTY_CAPTIONS);
  const audioRef = useRef<HTMLAudioElement>(null);
  const busy = status === CONNECTING_STATUS || status === CONNECTED_STATUS;

  async function onStart() {
    setCaptions(EMPTY_CAPTIONS);
    try {
      await startLiveCall({
        fetchSession,
        getUserMedia: requestMicrophone,
        RTCPeerConnection,
        attachRemoteTrack: (track) => playRemoteTrack(audioRef.current, track),
        onStatus: setStatus,
        onCaptions: setCaptions,
      });
    } catch (error) {
      setStatus(statusFromError(error));
    }
  }

  async function onStop() {
    await stopLiveCall();
  }

  return (
    <main>
      <h1>{PAGE_HEADING}</h1>
      <p>{ROLE_LINE}</p>
      <p id="call-status">{status}</p>
      <div className="call-controls">
        <button id="start-call" type="button" onClick={onStart} disabled={busy}>
          Start
        </button>
        <button
          id="stop-call"
          type="button"
          onClick={() => {
            void onStop();
          }}
          disabled={status !== CONNECTED_STATUS}
        >
          Stop
        </button>
      </div>
      <section className="caption-block">
        <h2>{YOU_LABEL}</h2>
        <p id="user-caption">{captions.user}</p>
      </section>
      <section className="caption-block">
        <h2>{AGENT_LABEL}</h2>
        <p id="assistant-caption">{captions.assistant}</p>
      </section>
      <p>{COST_NOTE}</p>
      <audio ref={audioRef} autoPlay />
    </main>
  );
}
