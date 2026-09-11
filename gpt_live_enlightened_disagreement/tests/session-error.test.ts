import { describe, expect, it } from "vitest";
import {
  LIVE_CREATE_FAILED,
  sessionFailureMessage,
} from "@/lib/live-webrtc";

describe("sessionFailureMessage", () => {
  it("reads the error field from session JSON", () => {
    const result = sessionFailureMessage(
      '{"error":"Set OPENAI_API_KEY on the server"}',
    );
    expect(result).toBe("Set OPENAI_API_KEY on the server");
  });

  it("returns Live session creation failed when the body is empty", () => {
    expect(sessionFailureMessage("   ")).toBe(LIVE_CREATE_FAILED);
  });

  it("returns the raw body when the text is not JSON", () => {
    expect(sessionFailureMessage("boom")).toBe("boom");
  });
});
