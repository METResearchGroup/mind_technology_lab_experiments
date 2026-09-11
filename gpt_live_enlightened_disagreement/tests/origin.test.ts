import { afterEach, describe, expect, it } from "vitest";
import { isAllowedOrigin } from "@/lib/origin";

const LOCALHOST = "http://localhost:3000";

describe("isAllowedOrigin", () => {
  const originalVercelUrl = process.env.VERCEL_URL;

  afterEach(() => {
    if (originalVercelUrl === undefined) {
      delete process.env.VERCEL_URL;
    } else {
      process.env.VERCEL_URL = originalVercelUrl;
    }
  });

  it("allows localhost", () => {
    const result = isAllowedOrigin(LOCALHOST);
    expect(result).toBe(true);
  });

  it("rejects an unexpected origin", () => {
    const result = isAllowedOrigin("https://evil.example");
    expect(result).toBe(false);
  });

  it("allows the Vercel deployment origin", () => {
    process.env.VERCEL_URL = "my-app.vercel.app";
    const result = isAllowedOrigin("https://my-app.vercel.app");
    expect(result).toBe(true);
  });

  it("rejects a null origin", () => {
    const result = isAllowedOrigin(null);
    expect(result).toBe(false);
  });
});
