export type SessionRequest = {
  origin: string | null;
  sdp: unknown;
};

export type LiveSessionBody = {
  mode: "live";
  session: { id: string };
  transport: { type: "webrtc"; sdp: string };
};

export type RealtimeSessionBody = {
  mode: "realtime";
  client_secret: string;
};

export type SessionErrorBody = {
  error: string;
};

export type SessionResponseBody =
  | LiveSessionBody
  | RealtimeSessionBody
  | SessionErrorBody;

export type SessionResult = {
  status: number;
  body: SessionResponseBody;
};

export type LiveCreateResult = {
  session: { id: string };
  transport: { type: "webrtc"; sdp: string };
};

export type SessionDeps = {
  getOpenAIKey?: () => string;
  createLiveSession?: (sdp: string) => Promise<LiveCreateResult>;
  createRealtimeClientSecret?: () => Promise<string>;
};

export async function createSessionFromSdp(
  _request: SessionRequest,
  _deps: SessionDeps = {},
): Promise<SessionResult> {
  throw new Error("not implemented");
}
