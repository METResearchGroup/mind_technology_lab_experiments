import { getAppOrigin } from "@/lib/env";

const LOCALHOST_ORIGIN = "http://localhost:3000";
const LOOPBACK_ORIGIN = "http://127.0.0.1:3000";
const HTTPS_PREFIX = "https://";

export function isAllowedOrigin(origin: string | null): boolean {
  if (!origin) {
    return false;
  }
  const allowed = new Set([
    getAppOrigin(),
    LOCALHOST_ORIGIN,
    LOOPBACK_ORIGIN,
  ]);
  const vercelHost = process.env.VERCEL_URL?.trim();
  if (vercelHost) {
    allowed.add(`${HTTPS_PREFIX}${vercelHost}`);
  }
  return allowed.has(origin);
}
