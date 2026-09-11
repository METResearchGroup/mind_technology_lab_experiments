export const UNEXPECTED_ORIGIN_ERROR = "Unexpected request origin";
export const MISSING_SDP_ERROR = "An SDP offer is required";
export const MISSING_KEY_ERROR = "Set OPENAI_API_KEY on the server";
export const LIVE_CREATE_FAILED_ERROR = "Live session creation failed";

export const STATUS_FORBIDDEN = 403;
export const STATUS_BAD_REQUEST = 400;
export const STATUS_SERVICE_UNAVAILABLE = 503;
export const STATUS_CREATED = 201;
export const STATUS_BAD_GATEWAY = 502;

export const LIVE_MODEL = "gpt-live-1";
export const LIVE_VOICE = "marin";
export const BACKEND_MODEL = "gpt-5.6-terra";
export const REALTIME_FALLBACK_MODEL = "gpt-realtime-2.1";
export const LIVE_FALLBACK_STATUSES = new Set([403, 404]);

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
