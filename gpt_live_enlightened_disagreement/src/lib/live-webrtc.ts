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
