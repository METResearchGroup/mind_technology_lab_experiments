import { createSessionFromSdp } from "@/lib/openai-live";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const payload = (await request.json()) as { sdp?: unknown };
  const result = await createSessionFromSdp({
    origin: request.headers.get("origin"),
    sdp: payload.sdp,
  });
  return Response.json(result.body, { status: result.status });
}
