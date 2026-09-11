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

export type LiveCallDeps = {
  fetchSession: (sdp: string) => Promise<Response>;
  getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  RTCPeerConnection: new () => RTCPeerConnection;
  attachRemoteTrack: (track: MediaStreamTrack) => void;
  onStatus: (status: string) => void;
  onEvent?: (event: { type: string; [key: string]: unknown }) => void;
};

export async function startLiveCall(_deps: LiveCallDeps): Promise<void> {
  throw new Error("not implemented");
}

export async function stopLiveCall(): Promise<void> {
  throw new Error("not implemented");
}
