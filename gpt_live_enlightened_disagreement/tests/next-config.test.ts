import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { PRINCIPLES_FILE_NAME } from "@/lib/prompt-file";

describe("next.config tracing", () => {
  it("includes the principles file for the session route", () => {
    const result = readFileSync("next.config.ts", "utf8");
    expect(result).toContain('"/api/session"');
    expect(result).toContain(`"./${PRINCIPLES_FILE_NAME}"`);
  });
});
