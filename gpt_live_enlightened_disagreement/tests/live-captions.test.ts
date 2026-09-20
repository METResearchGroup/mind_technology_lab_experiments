import { describe, expect, it } from "vitest";
import { applyTranscriptDelta } from "@/lib/live-captions";

const EMPTY = { user: "", assistant: "" };

describe("applyTranscriptDelta", () => {
  it("appends input deltas to the user caption", () => {
    const result = applyTranscriptDelta(EMPTY, {
      type: "session.input_transcript.delta",
      delta: "Hi",
    });
    expect(result).toEqual({ user: "Hi", assistant: "" });
  });

  it("appends output deltas to the assistant caption", () => {
    const withUser = applyTranscriptDelta(EMPTY, {
      type: "session.input_transcript.delta",
      delta: "Hi",
    });
    const result = applyTranscriptDelta(withUser, {
      type: "session.output_transcript.delta",
      delta: "Hello",
    });
    expect(result).toEqual({ user: "Hi", assistant: "Hello" });
  });

  it("keeps overlapping input and output captions", () => {
    const afterInput = applyTranscriptDelta(EMPTY, {
      type: "session.input_transcript.delta",
      delta: "User",
    });
    const result = applyTranscriptDelta(afterInput, {
      type: "session.output_transcript.delta",
      delta: "Agent",
    });
    expect(result.user).not.toBe("");
    expect(result.assistant).not.toBe("");
  });

  it("ignores session.started", () => {
    const result = applyTranscriptDelta(
      { user: "Hi", assistant: "Hello" },
      { type: "session.started" },
    );
    expect(result).toEqual({ user: "Hi", assistant: "Hello" });
  });
});
