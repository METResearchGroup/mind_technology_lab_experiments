"use client";

import { useEffect, useState, useTransition } from "react";
import { addNote } from "./actions";

type Note = {
  id?: number;
  body?: string;
  created_at?: string;
};

type Props = {
  apiBase: string;
};

export function DemoPanel({ apiBase }: Props) {
  const [healthText, setHealthText] = useState("Loading health…");
  const [notes, setNotes] = useState<Note[]>([]);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    const controller = new AbortController();
    const base = apiBase.replace(/\/$/, "");

    async function load() {
      try {
        const [healthResponse, notesResponse] = await Promise.all([
          fetch(`${base}/health`, { signal: controller.signal }),
          fetch(`${base}/api/notes`, { signal: controller.signal }),
        ]);
        const healthBody = await healthResponse.text();
        setHealthText(
          healthResponse.ok
            ? healthBody
            : `Health returned ${healthResponse.status}: ${healthBody}`,
        );
        if (!notesResponse.ok) {
          setNotesError(`Notes returned ${notesResponse.status}.`);
          setNotes([]);
          return;
        }
        const payload = (await notesResponse.json()) as { notes?: Note[] };
        setNotes(Array.isArray(payload.notes) ? payload.notes : []);
        setNotesError(null);
      } catch (error) {
        if (controller.signal.aborted) return;
        const detail = error instanceof Error ? error.message : "Request failed.";
        setHealthText(detail);
        setNotesError(detail);
      }
    }

    void load();
    return () => controller.abort();
  }, [apiBase, tick]);

  function onSubmit(formData: FormData) {
    startTransition(async () => {
      const result = await addNote(formData);
      setMessage(result.detail);
      if (result.ok) setTick((current) => current + 1);
    });
  }

  return (
    <div className="grid gap-6">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-semibold">Health, from the browser</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          The browser calls <code>{apiBase}/health</code> directly, so the API
          has to allow this page origin.
        </p>
        <pre className="mt-4 overflow-x-auto rounded bg-slate-100 p-3 text-sm">{healthText}</pre>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-semibold">Notes, from the browser</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Reading notes is public. Writing a note goes through this Worker, which
          attaches the token.
        </p>
        {notesError ? <p className="mt-4 text-sm text-red-700">{notesError}</p> : null}
        {notes.length === 0 && !notesError ? (
          <p className="mt-4 text-sm text-slate-600">No notes yet.</p>
        ) : (
          <ul className="mt-4 grid gap-3">
            {notes.map((note) => (
              <li className="rounded bg-slate-100 px-3 py-2 text-sm" key={note.id ?? note.body}>
                <p>{note.body}</p>
                <p className="mt-1 text-slate-500">{note.created_at}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-semibold">Save a note</h2>
        <form action={onSubmit} className="mt-4 grid gap-3">
          <label className="grid gap-2 text-sm" htmlFor="body">
            Note
            <input
              className="rounded border border-slate-300 px-3 py-2"
              id="body"
              maxLength={200}
              name="body"
              required
            />
          </label>
          <button
            className="w-fit rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
            disabled={pending}
            type="submit"
          >
            {pending ? "Saving…" : "Save"}
          </button>
        </form>
        {message ? <p className="mt-3 text-sm">{message}</p> : null}
      </section>
    </div>
  );
}
