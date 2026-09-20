import { getAppOrigin } from "@/lib/env";

const LOCALHOST_ORIGIN = "http://localhost:3000";
const LOOPBACK_ORIGIN = "http://127.0.0.1:3000";
const HTTPS_PREFIX = "https://";

function addHttpsHost(allowed: Set<string>, host: string | undefined): void {
  const trimmed = host?.trim();
  if (trimmed) {
    allowed.add(`${HTTPS_PREFIX}${trimmed}`);
  }
}

export function isAllowedOrigin(origin: string | null): boolean {
  if (!origin) {
    return false;
  }
  const allowed = new Set([
    getAppOrigin(),
    LOCALHOST_ORIGIN,
    LOOPBACK_ORIGIN,
  ]);
  addHttpsHost(allowed, process.env.VERCEL_URL);
  addHttpsHost(allowed, process.env.VERCEL_BRANCH_URL);
  return allowed.has(origin);
}
