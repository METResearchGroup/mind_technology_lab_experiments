import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  DEVILS_ADVOCATE_HEADING,
  MISSION_HEADING,
  NON_GOALS_HEADING,
  OPERATING_RULE_NAMES,
  OPERATING_RULES_HEADING,
  PRINCIPLES_MISSING_ERROR,
  PRINCIPLES_TITLE,
  readPrinciplesMarkdown,
} from "@/lib/prompt-file";
import { getBackendInstructions, getLiveInstructions } from "@/lib/prompts";

describe("readPrinciplesMarkdown", () => {
  it("returns the principles title from the app working directory", () => {
    const result = readPrinciplesMarkdown();
    expect(result).toContain(PRINCIPLES_TITLE);
  });

  it("throws when the markdown file is absent", () => {
    const cwd = mkdtempSync(path.join(tmpdir(), "principles-"));
    expect(() => readPrinciplesMarkdown(cwd)).toThrow(PRINCIPLES_MISSING_ERROR);
  });
});

describe("getLiveInstructions", () => {
  it("includes restate, steelman or strongest, and capitalism", () => {
    const result = getLiveInstructions().toLowerCase();
    expect(result).toContain("restate");
    expect(result.includes("steelman") || result.includes("strongest")).toBe(
      true,
    );
    expect(result).toContain("capitalis");
  });

  it("is shorter than the backend instructions", () => {
    expect(getLiveInstructions().length).toBeLessThan(
      getBackendInstructions().length,
    );
  });
});

describe("getBackendInstructions", () => {
  it("includes mission, non-goals, operating rules, and the procedure", () => {
    const result = getBackendInstructions();
    expect(result).toContain(MISSION_HEADING);
    expect(result).toContain(NON_GOALS_HEADING);
    expect(result).toContain(OPERATING_RULES_HEADING);
    expect(result).toContain(DEVILS_ADVOCATE_HEADING);
  });

  it("includes each of the twelve operating rule names", () => {
    const result = getBackendInstructions();
    for (const ruleName of OPERATING_RULE_NAMES) {
      expect(result).toContain(ruleName);
    }
  });

  it("does not invent a thirteenth operating rule", () => {
    const result = getBackendInstructions();
    expect(result.toLowerCase()).not.toContain("thirteenth rule");
    expect(result).not.toContain("Rule 13");
  });
});
