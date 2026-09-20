import { describe, expect, it } from "vitest";
import { createSessionFromSdp } from "@/lib/openai-live";

const ALLOWED_ORIGIN = "http://localhost:3000";
const OFFER_SDP = "offer";

function missingKey(): string {
  throw new Error("Set OPENAI_API_KEY on the server");
}

describe("createSessionFromSdp", () => {
  it("returns 400 when SDP is missing", async () => {
    const result = await createSessionFromSdp({
      origin: ALLOWED_ORIGIN,
      sdp: undefined,
    });
    expect(result.status).toBe(400);
    expect(result.body).toEqual({ error: "An SDP offer is required" });
  });

  it("returns 403 when the origin is disallowed", async () => {
    const result = await createSessionFromSdp({
      origin: "https://evil.example",
      sdp: OFFER_SDP,
    });
    expect(result.status).toBe(403);
    expect(result.body).toEqual({ error: "Unexpected request origin" });
  });

  it("returns 503 when the OpenAI key is missing", async () => {
    const result = await createSessionFromSdp(
      { origin: ALLOWED_ORIGIN, sdp: OFFER_SDP },
      { getOpenAIKey: missingKey },
    );
    expect(result.status).toBe(503);
    expect(result.body).toEqual({ error: "Set OPENAI_API_KEY on the server" });
  });

  it("returns 201 live when Live create succeeds", async () => {
    const result = await createSessionFromSdp(
      { origin: ALLOWED_ORIGIN, sdp: OFFER_SDP },
      {
        getOpenAIKey: () => "sk-test",
        createLiveSession: async () => ({
          session: { id: "live_1" },
          transport: { type: "webrtc", sdp: "answer" },
        }),
      },
    );
    expect(result.status).toBe(201);
    expect(result.body).toEqual({
      mode: "live",
      session: { id: "live_1" },
      transport: { type: "webrtc", sdp: "answer" },
    });
  });

  it("falls back to realtime when Live returns 404", async () => {
    const result = await createSessionFromSdp(
      { origin: ALLOWED_ORIGIN, sdp: OFFER_SDP },
      {
        getOpenAIKey: () => "sk-test",
        createLiveSession: async () => {
          throw { status: 404 };
        },
        createRealtimeClientSecret: async () => "ek_test",
      },
    );
    expect(result.status).toBe(201);
    expect(result.body).toEqual({
      mode: "realtime",
      client_secret: "ek_test",
    });
  });

  it("returns 502 when Live returns 500", async () => {
    const result = await createSessionFromSdp(
      { origin: ALLOWED_ORIGIN, sdp: OFFER_SDP },
      {
        getOpenAIKey: () => "sk-test",
        createLiveSession: async () => {
          throw { status: 500 };
        },
      },
    );
    expect(result.status).toBe(502);
    expect(result.body).toEqual({ error: "Live session creation failed" });
  });
});
