"use client";

import { useEffect, useState } from "react";
import { ALPHA_KEYS, GOALS, nearestAlphaKey } from "@/lib/goals";
import { qwenSteerRow } from "@/lib/qwen";
import { scoreUserLikeness } from "@/lib/style";

function writeParams(goal: string, alpha: string) {
  const params = new URLSearchParams(window.location.search);
  params.set("goal", goal);
  params.set("alpha", alpha);
  window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
}

export function SteeringLab() {
  const [goalId, setGoalId] = useState("furniture");
  const [alpha, setAlpha] = useState(0.2);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const nextGoal = params.get("goal");
    const nextAlpha = params.get("alpha");
    if (nextGoal) setGoalId(nextGoal);
    if (nextAlpha != null && nextAlpha !== "") setAlpha(Number(nextAlpha));
  }, []);

  const goal = GOALS.find((item) => item.id === goalId) ?? GOALS[0];
  const key = nearestAlphaKey(Number.isFinite(alpha) ? alpha : 0.2);
  const qwenRow = qwenSteerRow(goal.id, Number(key));
  const message = qwenRow?.text ?? goal.messages[key];
  const scores = qwenRow
    ? {
        brevity: qwenRow.brevity,
        informality: qwenRow.informality,
        information_pacing: qwenRow.information_pacing,
        mean: qwenRow.mean,
        word_count: qwenRow.word_count,
      }
    : scoreUserLikeness(message);
  const direction =
    Number(key) < 0 ? "assistant direction" : Number(key) === 0 ? "unsteered" : "user direction";

  function selectGoal(id: string) {
    setGoalId(id);
    writeParams(id, key);
  }

  function selectAlpha(nextKey: (typeof ALPHA_KEYS)[number]) {
    setAlpha(Number(nextKey));
    writeParams(goal.id, nextKey);
  }

  return (
    <section className="panel p-5 md:p-6" aria-labelledby="lab-title">
      <div className="flex flex-col gap-2">
        <p className="text-xs tracking-[0.18em] uppercase text-[var(--muted)]">
          Interactive lab
        </p>
        <h2 id="lab-title" className="text-2xl md:text-3xl">
          Steer a request along the user role vector
        </h2>
        <p className="max-w-3xl text-[var(--muted)]">
          The paper adds a scaled unit vector to hidden states:
          {" "}
          <span className="font-mono text-sm text-[var(--ink)]" translate="no">
            h̃ = h + α ∥h∥ v̂
          </span>
          . The lab shows first messages from Qwen 3.5 4B after steering layer
          11. Furniture at α=0.2 is the same goal as Figure 5, not the paper's
          9B transcript.
        </p>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="flex flex-col gap-5">
          <fieldset>
            <legend className="mb-2 text-sm text-[var(--muted)]">Task goal</legend>
            <div className="flex flex-wrap gap-2">
              {GOALS.map((item) => {
                const selected = item.id === goal.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selectGoal(item.id)}
                    className={`rounded-full border px-3 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                      selected
                        ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--bg)]"
                        : "border-[var(--line)] text-[var(--ink)] hover:border-[var(--muted)]"
                    }`}
                    aria-pressed={selected}
                  >
                    {item.goal}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div>
            <label htmlFor="alpha" className="flex justify-between text-sm">
              <span>Steering strength α</span>
              <span className="tabular font-mono">{key}</span>
            </label>
            <input
              id="alpha"
              name="alpha"
              type="range"
              min={0}
              max={ALPHA_KEYS.length - 1}
              step={1}
              value={Math.max(0, ALPHA_KEYS.indexOf(key))}
              onChange={(event) => {
                const nextKey = ALPHA_KEYS[Number(event.target.value)] ?? "0";
                selectAlpha(nextKey);
              }}
              className="mt-3 w-full"
              autoComplete="off"
              aria-valuetext={`alpha ${key}, ${direction}`}
            />
            <p className="mt-2 text-sm text-[var(--muted)]">
              {Number(key) < 0
                ? "Negative α pushes the simulator toward assistant-like wording."
                : Number(key) === 0
                  ? "α = 0 leaves the default simulator wording in place."
                  : "Positive α shortens the request and withholds extra details."}
            </p>
          </div>

          <figure className="rounded-xl border border-[var(--line)] bg-[var(--bg)] p-4">
            <figcaption className="mb-2 flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
              <span>Generated request</span>
              <span translate="no">{direction}</span>
              {qwenRow ? (
                <span>Qwen 3.5 4B</span>
              ) : goal.source === "paper" ? (
                <span>from the paper</span>
              ) : (
                <span>constructed for this dashboard</span>
              )}
            </figcaption>
            <blockquote className="text-lg leading-relaxed">{message}</blockquote>
          </figure>
        </div>

        <aside className="flex flex-col gap-3" aria-label="Lexical user-likeness scores">
          {[
            ["Brevity", scores.brevity],
            ["Informality", scores.informality],
            ["Information pacing", scores.information_pacing],
            ["Mean", scores.mean],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-xl border border-[var(--line)] p-3">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
                {label}
              </p>
              <p className="tabular mt-1 font-mono text-3xl">
                {Number(value).toFixed(2)}
              </p>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--line)]">
                <div
                  className="h-full bg-[var(--accent)]"
                  style={{ width: `${(Number(value) / 5) * 100}%` }}
                />
              </div>
            </div>
          ))}
          <p className="text-sm text-[var(--muted)]">
            Word count {scores.word_count}. These scores use the same cheap
            lexical rules as the Python stand-in judge, not GPT 5 Mini.
          </p>
        </aside>
      </div>
    </section>
  );
}
