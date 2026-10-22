"use server";

import { env } from "cloudflare:workers";

export type NoteResult = {
  ok: boolean;
  detail: string;
};

export async function addNote(formData: FormData): Promise<NoteResult> {
  const body = String(formData.get("body") ?? "").trim();
  if (!body) {
    return { ok: false, detail: "Write a short note first." };
  }
  if (body.length > 200) {
    return { ok: false, detail: "Notes are limited to 200 characters." };
  }

  const base = env.API_BASE_URL?.replace(/\/$/, "");
  const token = env.NOTE_TOKEN;
  if (!base || !token) {
    return {
      ok: false,
      detail: "API_BASE_URL or NOTE_TOKEN is not set on this Worker.",
    };
  }

  let response: Response;
  try {
    // Service bindings ignore the hostname and deliver the path to the API Worker.
    response = await env.API.fetch(`${base}/api/notes`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ body }),
    });
  } catch {
    return { ok: false, detail: "The API request failed before a response." };
  }

  if (!response.ok) {
    return { ok: false, detail: `The API returned status ${response.status}.` };
  }
  return { ok: true, detail: "Saved." };
}
