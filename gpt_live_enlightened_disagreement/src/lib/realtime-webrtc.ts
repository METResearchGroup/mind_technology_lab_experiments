export type RealtimeCallDeps = {
  clientSecret: string;
  getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
  RTCPeerConnection: new () => RTCPeerConnection;
  attachRemoteTrack: (track: MediaStreamTrack) => void;
  onStatus: (status: string) => void;
};

export async function startRealtimeCall(_deps: RealtimeCallDeps): Promise<void> {
  throw new Error("not implemented");
}

export async function stopRealtimeCall(): Promise<void> {
  throw new Error("not implemented");
}
