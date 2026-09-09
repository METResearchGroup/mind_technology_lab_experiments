"use client";

import { useMemo, useState } from "react";
import { EVENT_BANK, QUESTIONS, simulateAnswers } from "@/lib/heuristic";
import type { DashboardData, PlaygroundAgent } from "@/lib/types";

const LIKERT_LABELS = [
  "Strongly disagree",
  "Disagree",
  "Neither",
  "Agree",
  "Strongly agree",
];

export function AgentExplorer({ data }: { data: DashboardData }) {
  const [agentId, setAgentId] = useState(data.playground.agents[0]?.agent_id ?? "");
  const [variable, setVariable] = useState(data.playground.questions[2]?.variable ?? "LIFESAT");
  const agent = data.playground.agents.find((row) => row.agent_id === agentId) ?? data.playground.agents[0];
  if (!agent) return null;
  const retrieval = agent.retrievals.find((row) => row.variable === variable);
  const question = data.playground.questions.find((q) => q.variable === variable);
  const human = agent.answers.filter((row) => row.variable === variable);

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      <aside className="flex flex-col gap-3">
        <label className="text-sm text-[var(--muted)]">
          Agent
          <select
            className="chip mt-1 w-full"
            value={agent.agent_id}
            onChange={(event) => setAgentId(event.target.value)}
          >
            {data.playground.agents.map((row) => (
              <option key={row.agent_id} value={row.agent_id}>
                {row.agent_id} · {row.ses} SES
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-[var(--muted)]">
          Evaluation item
          <select
            className="chip mt-1 w-full"
            value={variable}
            onChange={(event) => setVariable(event.target.value)}
          >
            {data.playground.questions.map((row) => (
              <option key={row.variable} value={row.variable}>
                {row.variable}
              </option>
            ))}
          </select>
        </label>
        <p className="text-sm leading-6 text-[var(--muted)]">{agent.profile_text}</p>
      </aside>
      <div className="flex flex-col gap-5">
        <p className="text-lg leading-7">{question?.question}</p>
        <div className="flex flex-wrap gap-2">
          {human.map((row) => (
            <span key={row.wave} className="chip">
              wave {row.wave}: {row.answer}
            </span>
          ))}
        </div>
        <Timeline agent={agent} />
        <div>
          <h3 className="mb-2 text-xl">Retrieved events (K=5, α=0.9)</h3>
          <ol className="flex flex-col gap-2">
            {(retrieval?.hits ?? []).map((hit, index) => (
              <li key={hit.event_id} className="panel p-3 text-sm leading-6">
                <div className="flex flex-wrap justify-between gap-2 text-[var(--muted)]">
                  <span>
                    #{index + 1} · wave {hit.wave}
                  </span>
                  <span>
                    sim {hit.similarity.toFixed(2)} · recency {hit.recency.toFixed(2)} · score{" "}
                    {hit.score.toFixed(2)}
                  </span>
                </div>
                <p className="mt-1">{hit.statement}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

function Timeline({ agent }: { agent: PlaygroundAgent }) {
  const waves = [...new Set(agent.events.map((event) => event.wave))];
  return (
    <div className="flex flex-col gap-3">
      {waves.map((wave) => (
        <div key={wave} className="grid gap-2 md:grid-cols-[72px_1fr]">
          <p className="text-sm text-[var(--gold)]">wave {wave}</p>
          <ul className="flex flex-col gap-1 text-sm text-[var(--muted)]">
            {agent.events
              .filter((event) => event.wave === wave)
              .map((event) => (
                <li key={event.event_id}>
                  {event.section}: {event.question} — {event.answer}
                </li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function ComposePerson() {
  const [ses, setSes] = useState<"low" | "middle" | "high">("middle");
  const [individual, setIndividual] = useState(0.4);
  const [variable, setVariable] = useState("LIFESAT");
  const [picked, setPicked] = useState<Record<string, number>>({
    JOB: 4,
    HARD: 1,
    VOL: 4,
  });

  const events = useMemo(
    () =>
      EVENT_BANK.filter((event) => picked[event.code]).map((event) => ({
        question: event.question,
        intensity: picked[event.code],
      })),
    [picked],
  );
  const answers = simulateAnswers({ ses, individual, events, variable });
  const question = QUESTIONS.find((row) => row.variable === variable);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          {(["low", "middle", "high"] as const).map((level) => (
            <button
              key={level}
              type="button"
              className="chip"
              data-active={ses === level}
              onClick={() => setSes(level)}
            >
              {level} SES
            </button>
          ))}
        </div>
        <label className="text-sm text-[var(--muted)]">
          Individual residual (what a static label misses)
          <input
            type="range"
            min={-1.2}
            max={1.2}
            step={0.05}
            value={individual}
            onChange={(event) => setIndividual(Number(event.target.value))}
            className="mt-2 w-full"
          />
        </label>
        <label className="text-sm text-[var(--muted)]">
          Survey item
          <select
            className="chip mt-1 w-full"
            value={variable}
            onChange={(event) => setVariable(event.target.value)}
          >
            {QUESTIONS.map((row) => (
              <option key={row.variable} value={row.variable}>
                {row.variable}: {row.question}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-col gap-2">
          {EVENT_BANK.map((event) => (
            <label key={event.code} className="flex items-center justify-between gap-3 text-sm">
              <span>{event.question}</span>
              <select
                className="chip"
                value={picked[event.code] ?? 0}
                onChange={(change) => {
                  const next = Number(change.target.value);
                  setPicked((current) => {
                    const copy = { ...current };
                    if (next === 0) delete copy[event.code];
                    else copy[event.code] = next;
                    return copy;
                  });
                }}
              >
                <option value={0}>off</option>
                {[1, 2, 3, 4, 5].map((code) => (
                  <option key={code} value={code}>
                    {code} {LIKERT_LABELS[code - 1]}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </div>
      <div>
        <p className="mb-3 text-lg leading-7">{question?.question}</p>
        <dl className="flex flex-col gap-2">
          {Object.entries(answers).map(([method, answer]) => (
            <div key={method} className="panel flex items-center justify-between gap-3 p-3">
              <dt className={method === "LifeMem" ? "text-[var(--gold)]" : ""}>{method}</dt>
              <dd>{answer}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-sm leading-6 text-[var(--muted)]">
          Direct collapses to the midpoint. Profile uses only SES. Event RAG sees the five most
          relevant events. LifeMem keeps the whole trajectory in parametric memory and still retrieves
          question-specific evidence.
        </p>
      </div>
    </div>
  );
}
