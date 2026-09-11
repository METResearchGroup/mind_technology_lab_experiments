export const REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls";
export const REALTIME_OUTPUT_TRANSCRIPT =
  "response.output_audio_transcript.delta";
export const REALTIME_SDP_CONTENT_TYPE = "application/sdp";

export type RealtimeCallDeps = {
  clientSecret: string;
  getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  RTCPeerConnection: new () => RTCPeerConnection;
  attachRemoteTrack: (track: MediaStreamTrack) => void;
  onStatus: (status: string) => void;
};

type ActiveRealtimeCall = {
  peer: RTCPeerConnection;
  microphone: MediaStream;
};

let activeRealtime: ActiveRealtimeCall | null = null;

function cleanupRealtime(): void {
  if (!activeRealtime) {
    return;
  }
  activeRealtime.microphone.getTracks().forEach((track) => track.stop());
  activeRealtime.peer.close();
  activeRealtime = null;
}

export async function startRealtimeCall(deps: RealtimeCallDeps): Promise<void> {
  cleanupRealtime();
  const microphone = await deps.getUserMedia({ audio: true });
  const peer = new deps.RTCPeerConnection();
  peer.addEventListener("track", (event: Event) => {
    deps.attachRemoteTrack((event as RTCTrackEvent).track);
  });
  microphone.getAudioTracks().forEach((track) => peer.addTrack(track, microphone));
  peer.createDataChannel("oai-events");
  const offer = await peer.createOffer();
  await peer.setLocalDescription(offer);
  const sdp = peer.localDescription?.sdp;
  if (!sdp) {
    cleanupRealtime();
    throw new Error("Missing local SDP offer");
  }
  const response = await fetch(REALTIME_CALLS_URL, {
    method: "POST",
    body: sdp,
    headers: {
      Authorization: `Bearer ${deps.clientSecret}`,
      "Content-Type": REALTIME_SDP_CONTENT_TYPE,
    },
  });
  if (!response.ok) {
    cleanupRealtime();
    throw new Error(await response.text());
  }
  const answer = await response.text();
  await peer.setRemoteDescription({ type: "answer", sdp: answer });
  activeRealtime = { peer, microphone };
  deps.onStatus("Connected");
}

export async function stopRealtimeCall(): Promise<void> {
  cleanupRealtime();
}
