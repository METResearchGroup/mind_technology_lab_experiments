const DEFAULT_APP_ORIGIN = "http://localhost:3000";
const MISSING_OPENAI_KEY = "Set OPENAI_API_KEY on the server";

export function getOpenAIKey(): string {
  const key = process.env.OPENAI_API_KEY?.trim();
  if (!key) {
    throw new Error(MISSING_OPENAI_KEY);
  }
  return key;
}

export function getAppOrigin(): string {
  const origin = process.env.APP_ORIGIN?.trim();
  if (origin) {
    return origin;
  }
  return DEFAULT_APP_ORIGIN;
}
