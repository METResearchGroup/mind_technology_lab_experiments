"use client";

import { useEffect, useState } from "react";
import {
  AdapterScatter,
  IdentityScatter,
  LatencyChart,
  PaperMetricChart,
  ReplicationChart,
  SweepChart,
} from "@/components/charts";
import { AgentExplorer, ComposePerson } from "@/components/playground";
import {
  METRIC_KEYS,
  METHOD_LABELS,
  type DashboardData,
} from "@/lib/types";

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState("Llama-3.1-8B-Instruct");
  const [dataset, setDataset] = useState<"ah" | "us">("ah");
  const [paperMetric, setPaperMetric] = useState<"kl" | "wg" | "ent">("kl");
  const [repMetric, setRepMetric] = useState("kl");

  useEffect(() => {
    fetch("/data/results.json")
      .then((response) => {
        if (!response.ok) throw new Error(`Failed to load results (${response.status})`);
        return response.json();
      })
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-24">
        <h1 className="text-4xl">Could not load results</h1>
        <p className="mt-3 text-[var(--muted)]">{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-24">
        <p className="text-[var(--muted)]">Loading cohort atlas…</p>
      </main>
    );
  }

  const models = Object.keys(data.paper.table1);
  const ablation = data.paper.table2[model];

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-16 px-6 py-12">
      <header className="flex flex-col gap-6">
        <p className="text-sm tracking-[0.18em] text-[var(--gold)] uppercase">
          arXiv:2608.19621 · synthetic replication
        </p>
        <h1 className="max-w-4xl text-5xl leading-[1.05] md:text-6xl">
          Static labels make LLM agents essentialist. Life trajectories undo that.
        </h1>
        <p className="max-w-3xl text-lg leading-8 text-[var(--muted)]">
          {data.paper.paper.title}. Wang, Zhou, Du, Su, Cao, Pan, Ai, Wu, Zhang, Liu. This
          dashboard reports the paper’s published tables, a CPU-faithful replication on a
          24-person synthetic panel, and a Qwen/Qwen3.5-4B GPU path on Hugging Face Jobs.
          Restricted Add Health and Understanding Society files are not redistributed.
        </p>
        <div className="flex flex-wrap gap-3">
          <a className="chip" href={data.paper.paper.arxiv}>
            Paper
          </a>
          <a className="chip" href={data.paper.paper.code}>
            Official code
          </a>
          <a className="chip" href="https://www.alphaxiv.org/abs/2608.19621">
            alphaXiv
          </a>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        {data.takeaways.map((item) => (
          <article key={item.id} className="panel flex flex-col gap-3 p-5">
            <p className="text-4xl text-[var(--gold)]">{item.stat}</p>
            <h2 className="text-2xl">{item.title}</h2>
            <p className="text-sm leading-6 text-[var(--muted)]">{item.body}</p>
            <p className="text-xs tracking-wide text-[var(--faint)] uppercase">
              {item.stat_label}
            </p>
          </article>
        ))}
      </section>

      <section className="flex flex-col gap-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-4xl">Paper results</h2>
            <p className="mt-2 max-w-2xl text-[var(--muted)]">
              Table 1, Llama / Ministral / Qwen3.5-9B, 100 respondents per survey. Lower is better
              on every metric.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {models.map((name) => (
              <button
                key={name}
                type="button"
                className="chip"
                data-active={model === name}
                onClick={() => setModel(name)}
              >
                {name.replace("-Instruct", "").replace("-2512", "")}
              </button>
            ))}
            <button
              type="button"
              className="chip"
              data-active={dataset === "ah"}
              onClick={() => setDataset("ah")}
            >
              Add Health
            </button>
            <button
              type="button"
              className="chip"
              data-active={dataset === "us"}
              onClick={() => setDataset("us")}
            >
              Understanding Society
            </button>
            {(["kl", "wg", "ent"] as const).map((metric) => (
              <button
                key={metric}
                type="button"
                className="chip"
                data-active={paperMetric === metric}
                onClick={() => setPaperMetric(metric)}
              >
                {metric}
              </button>
            ))}
          </div>
        </div>
        <div className="panel p-4">
          <PaperMetricChart data={data} model={model} dataset={dataset} metric={paperMetric} />
        </div>
        <AblationTable ablation={ablation} dataset={dataset} />
      </section>

      <section className="flex flex-col gap-5">
        <div>
          <h2 className="text-4xl">Identity clouds</h2>
          <p className="mt-2 max-w-3xl text-[var(--muted)]">
            Concatenated last-wave answers, PCA, colored by SES. Humans overlap. Profile agents
            collapse onto class centroids — the essentialism pattern from Figure 1. LifeMem
            restores overlap.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="panel p-4">
            <IdentityScatter cloud={data.replication.identity.human} title="Synthetic humans" />
          </div>
          <div className="panel p-4">
            <IdentityScatter cloud={data.replication.identity.profile} title="Profile agents" />
          </div>
          <div className="panel p-4">
            <IdentityScatter cloud={data.replication.identity.lifemem} title="LifeMem agents" />
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-5">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-4xl">Synthetic replication</h2>
            <p className="mt-2 max-w-2xl text-[var(--muted)]">
              24 agents, 6 waves, 8 evaluation items. Same metrics, K=5, α=0.9. The respondent is
              a prompt-conditioned heuristic, not a GPU LLM — Add Health microdata cannot ship
              with this repo.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {METRIC_KEYS.map((metric) => (
              <button
                key={metric.id}
                type="button"
                className="chip"
                data-active={repMetric === metric.id}
                onClick={() => setRepMetric(metric.id)}
              >
                {metric.label}
              </button>
            ))}
          </div>
        </div>
        <div className="panel p-4">
          <ReplicationChart data={data} metric={repMetric} />
        </div>
        <ReplicationTable methods={data.replication.methods} />
      </section>

      <GpuSection data={data} metric={repMetric} />

      <section className="flex flex-col gap-5">
        <div>
          <h2 className="text-4xl">Compose a person</h2>
          <p className="mt-2 max-w-3xl text-[var(--muted)]">
            Same scoring rules as the CPU replication. Change class, residual individuality, and
            life events, then watch Direct, Profile, Event RAG, and LifeMem answer a Likert item.
          </p>
        </div>
        <div className="panel p-5">
          <ComposePerson />
        </div>
      </section>

      <section className="flex flex-col gap-5">
        <div>
          <h2 className="text-4xl">Structured memory playground</h2>
          <p className="mt-2 max-w-3xl text-[var(--muted)]">
            Score(q, e) = cosine(question, event) × α^(t − τ). LifeMem retrieves the top five
            events, then keeps the rest in the adapter.
          </p>
        </div>
        <div className="panel p-5">
          <AgentExplorer data={data} />
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="panel p-5">
          <h2 className="mb-2 text-3xl">Inference latency (Llama-8B)</h2>
          <p className="mb-4 text-sm text-[var(--muted)]">
            Table 3. Event RAG pays for bge-m3. LifeMem is 6.8× faster on Add Health.
          </p>
          <LatencyChart data={data} />
        </div>
        <div className="panel p-5">
          <h2 className="mb-2 text-3xl">Adapter trajectories</h2>
          <p className="mb-4 text-sm text-[var(--muted)]">
            PCA of the hashed parametric state after each wave. Later waves fan out as biographies
            diverge — the paper’s LoRA-state plot, on dummy adapters.
          </p>
          <AdapterScatter data={data} />
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        <div className="panel p-5">
          <h2 className="mb-2 text-2xl">Temporal decay α</h2>
          <p className="mb-3 text-sm text-[var(--muted)]">Table 12. Main setting is 0.9.</p>
          <SweepChart rows={data.paper.table12_decay} xKey="alpha" />
        </div>
        <div className="panel p-5">
          <h2 className="mb-2 text-2xl">Replay weight η</h2>
          <p className="mb-3 text-sm text-[var(--muted)]">Table 13. Main setting is 0.5.</p>
          <SweepChart rows={data.paper.table13_replay} xKey="eta" />
        </div>
        <div className="panel p-5">
          <h2 className="mb-2 text-2xl">LoRA rank</h2>
          <p className="mb-3 text-sm text-[var(--muted)]">
            Table 15. r=32 is best; the paper keeps r=8 for storage.
          </p>
          <SweepChart rows={data.paper.table15_rank} xKey="rank" />
        </div>
      </section>

      <section className="panel p-5">
        <h2 className="text-3xl">What this replication is</h2>
        <ul className="mt-4 flex flex-col gap-3 text-[var(--muted)] leading-7">
          <li>{data.notes.restricted_data}</li>
          <li>{data.notes.encoder}</li>
          <li>{data.notes.parametric_memory}</li>
          <li>{data.notes.decay}</li>
        </ul>
      </section>

      <footer className="pb-10 text-sm text-[var(--faint)]">
        Mind Technology Lab replication · default open model Qwen/Qwen3.5-4B for any GPU follow-up.
      </footer>
    </main>
  );
}

function GpuSection({ data, metric }: { data: DashboardData; metric: string }) {
  const gpu = data.gpu;
  if (!gpu) return null;
  const methods = gpu.methods;
  return (
    <section className="flex flex-col gap-5">
      <div>
        <h2 className="text-4xl">Qwen 4B GPU run</h2>
        <p className="mt-2 max-w-3xl text-[var(--muted)]">
          Hugging Face Jobs, {gpu.model ?? "Qwen/Qwen3.5-4B"}, per-agent LoRA rank 8.{" "}
          {gpu.status === "completed"
            ? `${gpu.n_agents ?? gpu.config?.n_agents} agents on ${gpu.device ?? gpu.flavor ?? "GPU"}.`
            : gpu.status === "blocked"
              ? "The job script is ready; submitting it still needs Jobs credits on the Hugging Face namespace."
              : "Waiting for gpu_results.json from the Jobs runner."}
        </p>
      </div>
      {methods ? (
        <>
          <div className="panel p-4">
            <ReplicationChart data={data} metric={metric} methods={methods} />
          </div>
          <ReplicationTable methods={methods} />
        </>
      ) : (
        <div className="panel p-5 text-sm leading-7 text-[var(--muted)]">
          <p>Status: {gpu.status}</p>
          {gpu.url ? (
            <p>
              Job:{" "}
              <a className="text-[var(--gold)]" href={gpu.url}>
                {gpu.url}
              </a>
            </p>
          ) : null}
          {gpu.error ? <p>{gpu.error}</p> : null}
          {gpu.hint ? <p>{gpu.hint}</p> : null}
        </div>
      )}
    </section>
  );
}

function AblationTable({
  ablation,
  dataset,
}: {
  ablation: DashboardData["paper"]["table2"][string];
  dataset: "ah" | "us";
}) {
  if (!ablation) return null;
  const prefix = dataset;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-[var(--muted)]">
          <tr>
            <th className="py-2">Variant</th>
            <th>KL</th>
            <th>WG gap</th>
            <th>Entropy gap</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(ablation).map(([name, row]) => (
            <tr key={name} className="border-t border-[var(--line)]">
              <td className="py-2">{name}</td>
              <td>{row[`${prefix}_kl`].toFixed(3)}</td>
              <td>{row[`${prefix}_wg`].toFixed(3)}</td>
              <td>{row[`${prefix}_ent`].toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReplicationTable({
  methods,
}: {
  methods: DashboardData["replication"]["methods"];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-[var(--muted)]">
          <tr>
            <th className="py-2">Method</th>
            <th>KL</th>
            <th>WG gap</th>
            <th>Entropy gap</th>
            <th>Transition JS</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(methods).map(([name, row]) => (
            <tr key={name} className="border-t border-[var(--line)]">
              <td className="py-2">{METHOD_LABELS[name] ?? name}</td>
              <td>{row.kl.toFixed(3)}</td>
              <td>{row.wg_gap.toFixed(3)}</td>
              <td>{row.entropy_gap.toFixed(3)}</td>
              <td>{row.transition_js?.toFixed(3) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
