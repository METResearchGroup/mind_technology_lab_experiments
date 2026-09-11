import OpenAI from "openai";
import { getOpenAIKey } from "@/lib/env";
import { isAllowedOrigin } from "@/lib/origin";
import { getBackendInstructions, getLiveInstructions } from "@/lib/prompts";

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

function errorResult(status: number, message: string): SessionResult {
  return { status, body: { error: message } };
}

function readSdpOffer(sdp: unknown): string | null {
  if (typeof sdp !== "string" || !sdp.trim()) {
    return null;
  }
  return sdp;
}

function readApiKey(deps: SessionDeps): string | null {
  try {
    const readKey = deps.getOpenAIKey ?? getOpenAIKey;
    return readKey();
  } catch {
    return null;
  }
}

function responsesDelegation() {
  return {
    type: "responses" as const,
    responses: {
      model: BACKEND_MODEL,
      instructions: getBackendInstructions(),
      tools: [{ type: "web_search" as const }],
      tool_choice: "auto" as const,
    },
  };
}

export async function defaultCreateLiveSession(
  sdp: string,
): Promise<LiveCreateResult> {
  const client = new OpenAI({ apiKey: getOpenAIKey(), maxRetries: 0 });
  const result = await client.live.create({
    session: {
      model: LIVE_MODEL,
      instructions: getLiveInstructions(),
      audio: { output: { voice: LIVE_VOICE } },
      delegation: responsesDelegation(),
    },
    transport: { type: "webrtc", sdp },
  });
  return {
    session: { id: result.session.id },
    transport: { type: "webrtc", sdp: result.transport.sdp },
  };
}

function liveSuccess(result: LiveCreateResult): SessionResult {
  return {
    status: STATUS_CREATED,
    body: {
      mode: "live",
      session: { id: result.session.id },
      transport: { type: "webrtc", sdp: result.transport.sdp },
    },
  };
}

export async function createSessionFromSdp(
  request: SessionRequest,
  deps: SessionDeps = {},
): Promise<SessionResult> {
  if (!isAllowedOrigin(request.origin)) {
    return errorResult(STATUS_FORBIDDEN, UNEXPECTED_ORIGIN_ERROR);
  }
  const sdp = readSdpOffer(request.sdp);
  if (!sdp) {
    return errorResult(STATUS_BAD_REQUEST, MISSING_SDP_ERROR);
  }
  if (!readApiKey(deps)) {
    return errorResult(STATUS_SERVICE_UNAVAILABLE, MISSING_KEY_ERROR);
  }
  const createLive = deps.createLiveSession ?? defaultCreateLiveSession;
  const live = await createLive(sdp);
  return liveSuccess(live);
}
