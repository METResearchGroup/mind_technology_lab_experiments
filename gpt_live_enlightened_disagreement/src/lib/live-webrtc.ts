import { applyTranscriptDelta, type CaptionState } from "@/lib/live-captions";
import { startRealtimeCall } from "@/lib/realtime-webrtc";

export const LIVE_DATA_CHANNEL = "oai-events";
export const ICE_GATHER_TIMEOUT_MS = 10_000;
export const SESSION_CLOSE_TIMEOUT_MS = 15_000;
export const SESSION_STARTED = "session.started";
export const SESSION_CLOSED = "session.closed";
export const SESSION_CLOSE = "session.close";
export const ICE_TIMEOUT_ERROR = "Timed out while gathering ICE candidates";
export const LIVE_CREATE_FAILED = "Live session creation failed";
export const INCOMPLETE_FINALIZATION =
  "Incomplete finalization: no session.closed event.";
export const CONVERSATION_ENDED = "Conversation ended.";
export const FINISHING_CONVERSATION = "Finishing the conversation…";
export const CONNECTING_STATUS = "Connecting";
export const CONNECTED_STATUS = "Connected";

export type LiveCallDeps = {
  fetchSession: (sdp: string) => Promise<Response>;
  getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  RTCPeerConnection: new () => RTCPeerConnection;
  attachRemoteTrack: (track: MediaStreamTrack) => void;
  onStatus: (status: string) => void;
  onEvent?: (event: { type: string; [key: string]: unknown }) => void;
  onCaptions?: (state: CaptionState) => void;
};

type ParsedLiveEvent = {
  type: string;
  [key: string]: unknown;
};

type ActiveCall = {
  peer: RTCPeerConnection;
  channel: RTCDataChannel;
  microphone: MediaStream;
  started: boolean;
  finalized: boolean;
  onStatus: (status: string) => void;
  onEvent?: LiveCallDeps["onEvent"];
  onCaptions?: LiveCallDeps["onCaptions"];
  captions: CaptionState;
  startedWaiters: Array<() => void>;
  closeTimer?: ReturnType<typeof setTimeout>;
  closeWaiters: Array<() => void>;
};

let activeCall: ActiveCall | null = null;

function cleanup(): void {
  const call = activeCall;
  if (!call) {
    return;
  }
  if (call.closeTimer) {
    clearTimeout(call.closeTimer);
  }
  call.microphone.getTracks().forEach((track) => track.stop());
  call.channel.close();
  call.peer.close();
  activeCall = null;
}

async function waitForIce(peer: RTCPeerConnection): Promise<void> {
  if (peer.iceGatheringState === "complete") {
    return;
  }
  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      peer.removeEventListener("icegatheringstatechange", onState);
      reject(new Error(ICE_TIMEOUT_ERROR));
    }, ICE_GATHER_TIMEOUT_MS);
    function onState() {
      if (peer.iceGatheringState !== "complete") {
        return;
      }
      clearTimeout(timeout);
      peer.removeEventListener("icegatheringstatechange", onState);
      resolve();
    }
    peer.addEventListener("icegatheringstatechange", onState);
    onState();
  });
}

async function readSessionPayload(response: Response): Promise<{
  mode: string;
  transport?: { sdp?: string };
  client_secret?: string;
}> {
  const text = await response.text();
  if (!response.ok) {
    throw new Error(text.trim() || LIVE_CREATE_FAILED);
  }
  return JSON.parse(text) as {
    mode: string;
    transport?: { sdp?: string };
    client_secret?: string;
  };
}

function waitUntilStarted(call: ActiveCall): Promise<void> {
  if (call.started) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    call.startedWaiters.push(resolve);
  });
}

function handleLiveEvent(call: ActiveCall, raw: string): void {
  const event = JSON.parse(raw) as ParsedLiveEvent;
  call.onEvent?.(event);
  call.captions = applyTranscriptDelta(call.captions, event);
  call.onCaptions?.(call.captions);
  if (event.type === SESSION_STARTED) {
    call.started = true;
    call.onStatus(CONNECTED_STATUS);
    call.startedWaiters.forEach((resolve) => resolve());
    call.startedWaiters = [];
    return;
  }
  if (event.type === SESSION_CLOSED) {
    call.finalized = true;
    call.onStatus(CONVERSATION_ENDED);
    call.closeWaiters.forEach((resolve) => resolve());
    call.closeWaiters = [];
    cleanup();
  }
}

function bindChannel(call: ActiveCall): void {
  call.channel.addEventListener("message", (event: Event) => {
    const message = event as MessageEvent<string>;
    handleLiveEvent(call, message.data);
  });
}

async function negotiateLive(
  peer: RTCPeerConnection,
  sdpAnswer: string,
  call: ActiveCall,
): Promise<void> {
  await peer.setRemoteDescription({ type: "answer", sdp: sdpAnswer });
  await waitUntilStarted(call);
}

export async function startLiveCall(deps: LiveCallDeps): Promise<void> {
  cleanup();
  deps.onStatus(CONNECTING_STATUS);
  const microphone = await deps.getUserMedia({ audio: true });
  const peer = new deps.RTCPeerConnection();
  peer.addEventListener("track", (event: Event) => {
    const trackEvent = event as RTCTrackEvent;
    deps.attachRemoteTrack(trackEvent.track);
  });
  microphone.getAudioTracks().forEach((track) => peer.addTrack(track, microphone));
  const channel = peer.createDataChannel(LIVE_DATA_CHANNEL);
  const call: ActiveCall = {
    peer,
    channel,
    microphone,
    started: false,
    finalized: false,
    onStatus: deps.onStatus,
    onEvent: deps.onEvent,
    onCaptions: deps.onCaptions,
    captions: { user: "", assistant: "" },
    startedWaiters: [],
    closeWaiters: [],
  };
  activeCall = call;
  bindChannel(call);
  const offer = await peer.createOffer();
  await peer.setLocalDescription(offer);
  await waitForIce(peer);
  const localSdp = peer.localDescription?.sdp;
  if (!localSdp) {
    cleanup();
    throw new Error(LIVE_CREATE_FAILED);
  }
  const payload = await readSessionPayload(await deps.fetchSession(localSdp));
  if (payload.mode === "realtime") {
    cleanup();
    await startRealtimeCall({
      clientSecret: payload.client_secret ?? "",
      getUserMedia: deps.getUserMedia,
      RTCPeerConnection: deps.RTCPeerConnection,
      attachRemoteTrack: deps.attachRemoteTrack,
      onStatus: deps.onStatus,
    });
    return;
  }
  await negotiateLive(peer, payload.transport?.sdp ?? "", call);
}

export async function stopLiveCall(): Promise<void> {
  cleanup();
}
