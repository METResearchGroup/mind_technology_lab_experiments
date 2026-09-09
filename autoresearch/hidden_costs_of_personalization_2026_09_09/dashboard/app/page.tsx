"use client";

import { useEffect, useMemo, useState } from "react";
import data from "../data/replication.json";
import {
  coveredAnswers,
  normalize1to5,
  scoreIrp,
  scoreSycophancy,
  usefulItemRecall,
} from "../lib/metrics";
import {
  RISK_LABEL,
  SETTING_LABEL,
  SETTINGS,
  type PlaygroundItem,
  type ReplicationData,
  type RiskType,
  type Setting,
} from "../lib/types";

const DATA = data as unknown as ReplicationData;

const PAPER_ABSTRACT = {
  irp: 45.9,
  uir: 41.7,
  syco: 61.7,
};

function metricForRisk(risk: RiskType): "irp" | "uir" | "syco" {
  if (risk === "irrelevant_personalization") return "irp";
  if (risk === "preference_narrowing") return "uir";
  return "syco";
}

function SlopeChart({ risk }: { risk: RiskType }) {
  const key = metricForRisk(risk);
  const rows = [...DATA.paper_table_2].sort(
    (a, b) => a[key].profile_only - b[key].profile_only,
  );
  const width = 720;
  const height = 28 * rows.length + 36;
  const left = 210;
  const right = 620;
  const yFor = (i: number) => 24 + i * 28;
  const xFor = (v: number) => left + (v / 100) * (right - left);

  return (
    <svg className="slope" viewBox={`0 0 ${width} ${height}`} role="img">
      <title>{`Base versus profile ${RISK_LABEL[risk]} for 13 models`}</title>
      {[0, 50, 100].map((tick) => (
        <g key={tick}>
          <line
            x1={xFor(tick)}
            y1={18}
            x2={xFor(tick)}
            y2={height - 8}
            stroke="#c9b89a"
            strokeDasharray="2 4"
          />
          <text x={xFor(tick) - 8} y={14} fontSize="10" fill="#5c4e42">
            {tick}
          </text>
        </g>
      ))}
      {rows.map((row, i) => {
        const y = yFor(i);
        const x0 = xFor(row[key].base);
        const x1 = xFor(row[key].profile_only);
        return (
          <g key={row.model}>
            <text x={8} y={y + 4} fontSize="12">
              {row.model}
            </text>
            <line
              x1={x0}
              y1={y}
              x2={x1}
              y2={y}
              stroke="#1a1410"
              strokeWidth="1.5"
            />
            <circle cx={x0} cy={y} r="3.5" fill="#3f5c45" />
            <circle cx={x1} cy={y} r="3.5" fill="#b42318" />
            <text x={Math.max(x0, x1) + 8} y={y + 4} fontSize="11" fill="#b42318">
              {row[key].profile_only.toFixed(1)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function MiniBars() {
  const rows = DATA.aggregate.rows;
  const value = (risk: RiskType, setting: Setting) => {
    const row = rows.find(
      (item) => item.risk_type === risk && item.setting === setting,
    );
    if (!row) return 0;
    if (risk === "irrelevant_personalization") return row.irp_resistance_pct ?? 0;
    if (risk === "preference_narrowing") return row.uir_pct ?? 0;
    return row.syco_resistance_pct ?? 0;
  };
  const risks: RiskType[] = [
    "irrelevant_personalization",
    "preference_narrowing",
    "sycophantic_bias",
  ];
  return (
    <div className="compare">
      {risks.map((risk) => (
        <div key={risk}>
          <h3>{RISK_LABEL[risk]}</h3>
          <div className="bars" style={{ height: 120 }}>
            {SETTINGS.map((setting) => {
              const v = value(risk, setting);
              const tone =
                setting === "profile_only"
                  ? "profile"
                  : setting === "retrieval_only"
                    ? "memory"
                    : setting === "profile_retrieval"
                      ? "both"
                      : "";
              return (
                <div
                  key={setting}
                  className={`bar ${tone}`}
                  style={{ height: `${Math.max(8, v)}%` }}
                  title={`${SETTING_LABEL[setting]} ${v}`}
                >
                  <span>
                    {SETTING_LABEL[setting]} {v.toFixed(0)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function liveScores(item: PlaygroundItem, response: string) {
  const preferences = item.preferences ?? [];
  const attributes: Record<string, string> = {};
  for (const [key, value] of Object.entries(item.attributes)) {
    if (value) attributes[key] = value;
  }
  if (item.risk_type === "irrelevant_personalization") {
    const irp = scoreIrp(response, attributes, preferences, item.risk_type);
    return {
      primary: `${normalize1to5(irp.score).toFixed(0)}% IRP resistance`,
      detail: irp.flags.length
        ? `Injected: ${irp.flags.join(", ")}`
        : "No profile leakage",
    };
  }
  if (item.risk_type === "preference_narrowing") {
    const covered = coveredAnswers(response, item.universal_answers);
    const uir = usefulItemRecall(covered, item.useful_answers) * 100;
    return {
      primary: `${uir.toFixed(0)}% useful-item recall`,
      detail: covered.length
        ? `Covered ${covered.join(", ")}`
        : "No canonical options detected",
    };
  }
  const syco = scoreSycophancy(response, {
    userIsAtFault: Boolean(item.user_is_at_fault),
    statedPreference: item.stated_preference,
    preferences,
  });
  return {
    primary: `${normalize1to5(syco.score).toFixed(0)}% sycophancy resistance`,
    detail: syco.pis
      ? "PIS=1 preference-shaped"
      : "PIS=0 not preference-shaped",
  };
}

function Playground() {
  const cases = useMemo(() => {
    const ids = [...new Set(DATA.playground.map((item) => item.record_id))];
    return ids.map((id) => DATA.playground.find((item) => item.record_id === id)!);
  }, []);
  const [caseId, setCaseId] = useState(cases[0].record_id);
  const [setting, setSetting] = useState<Setting>("profile_only");
  const selected =
    DATA.playground.find(
      (item) => item.record_id === caseId && item.setting === setting,
    ) ?? DATA.playground[0];
  const [response, setResponse] = useState(selected.response);

  useEffect(() => {
    setResponse(selected.response);
  }, [selected.record_id, selected.setting, selected.response]);

  const live = liveScores(selected, response);
  const memories = selected.retrieved_memories ?? [];
  const cannedScore =
    selected.irp_resistance_pct ??
    selected.uir_pct ??
    selected.syco_resistance_pct;

  return (
    <div className="playground-grid">
      <div className="side-list">
        {cases.map((item) => (
          <button
            key={item.record_id}
            type="button"
            aria-current={item.record_id === caseId}
            onClick={() => setCaseId(item.record_id)}
          >
            <strong>{item.question}</strong>
            <div className="note">
              {RISK_LABEL[item.risk_type]}, {item.persona}
            </div>
          </button>
        ))}
      </div>
      <div>
        <div className="toolbar" role="group" aria-label="Personalization setting">
          {SETTINGS.map((value) => (
            <button
              key={value}
              type="button"
              className="chip"
              aria-pressed={setting === value}
              onClick={() => setSetting(value)}
            >
              {SETTING_LABEL[value]}
            </button>
          ))}
        </div>
        <p className="note">{selected.persona}</p>
        <h3>Prompt sent to the model</h3>
        <pre className="prompt">{selected.prompt}</pre>
        {memories.length > 0 ? (
          <>
            <h3>Retrieved memories</h3>
            <ul className="memory-list">
              {memories.map((memory) => (
                <li key={memory}>{memory}</li>
              ))}
            </ul>
          </>
        ) : null}
        <h3>Response (editable, scores update live)</h3>
        <textarea
          value={response}
          onChange={(event) => setResponse(event.target.value)}
          aria-label="Model response"
        />
        <div className="score-pills">
          <div className="pill">
            Live judge
            <strong>{live.primary}</strong>
          </div>
          <div className="pill">
            Mini-run
            <strong>{cannedScore}%</strong>
          </div>
        </div>
        <p className="note">{live.detail}</p>
        {selected.router_decision ? (
          <p className="note">Router: {selected.router_decision}</p>
        ) : null}
      </div>
    </div>
  );
}

function PaperTable({ risk }: { risk: RiskType }) {
  const key = metricForRisk(risk);
  const rows = [...DATA.paper_table_2].sort(
    (a, b) => a[key].profile_only - b[key].profile_only,
  );
  return (
    <div className="table-wrap">
      <table>
        <caption>
          Table 2 resistance scores for {RISK_LABEL[risk]} (higher is better)
        </caption>
        <thead>
          <tr>
            <th scope="col">Model</th>
            <th scope="col">Base</th>
            <th scope="col">Profile</th>
            <th scope="col">Memory</th>
            <th scope="col">Both</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.model}>
              <th scope="row">{row.model}</th>
              <td>{row[key].base.toFixed(1)}</td>
              <td>{row[key].profile_only.toFixed(1)}</td>
              <td>{row[key].retrieval_only.toFixed(1)}</td>
              <td>{row[key].profile_retrieval.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Page() {
  const [risk, setRisk] = useState<RiskType>("sycophantic_bias");
  const drops = DATA.paper_mean_drops;
  const benchmarks = DATA.paper_benchmark_accuracy ?? [];

  return (
    <main className="shell">
      <header className="masthead">
        <div>
          <p className="kicker">PRISK mini-replication, arXiv:2608.28833</p>
          <h1>Hidden costs of LLM personalization</h1>
        </div>
        <div className="meta">
          <div>Wang, Wu, Qian, Fan, Ha, Wu, Liu, Ji, Wang</div>
          <div>
            Seed set: {DATA.n_cases} cases × 4 settings
          </div>
          <div>Generator: {DATA.model_name}</div>
        </div>
      </header>

      <p className="lede">
        Conditioning a model on a user profile or retrieved memory is supposed
        to help. On this benchmark it also injects irrelevant attributes,
        shrinks the option set, and agrees with the user when it should push
        back.
      </p>

      <section className="stat-row" aria-label="Paper-reported average degradation">
        <article className="stat">
          <b>{PAPER_ABSTRACT.irp}%</b>
          <span>IRP degradation reported in the abstract across 13 models.</span>
        </article>
        <article className="stat">
          <b>{PAPER_ABSTRACT.uir}%</b>
          <span>Preference-narrowing degradation (useful-item recall).</span>
        </article>
        <article className="stat">
          <b>{PAPER_ABSTRACT.syco}%</b>
          <span>Sycophancy degradation, mostly from profile context.</span>
        </article>
      </section>

      <section className="panel">
        <h2>Table 2: base vs profile</h2>
        <p>
          Each line is one model. Green is the no-context score. Red is
          profile-only. Mean base-to-profile drops in this transcription are
          IRP {drops.irp_drop_pct}, UIR {drops.uir_drop_pct}, and sycophancy{" "}
          {drops.syco_drop_pct}. Those Table 2 means are not the same numbers as
          the abstract averages above.
        </p>
        <div className="toolbar" role="group" aria-label="Risk dimension">
          {(Object.keys(RISK_LABEL) as RiskType[]).map((value) => (
            <button
              key={value}
              type="button"
              className="chip"
              aria-pressed={risk === value}
              onClick={() => setRisk(value)}
            >
              {RISK_LABEL[value]}
            </button>
          ))}
        </div>
        <p className="legend">
          <span className="swatch olive" /> Base (no profile)
          <span className="swatch mark" /> Profile-only
        </p>
        <div className="chart-wrap">
          <SlopeChart risk={risk} />
        </div>
        <PaperTable risk={risk} />
      </section>

      {benchmarks.length > 0 ? (
        <section className="panel">
          <h2>Task accuracy still drops a little</h2>
          <p>
            Table 1 in the paper measures GSM8K, CommonsenseQA, and MMLU with
            and without a profile. The personalization tax is smaller here than
            on the risk metrics, but the profile still costs a few points.
          </p>
          <div className="table-wrap">
            <table>
              <caption>Published task accuracy, base versus profile</caption>
              <thead>
                <tr>
                  <th scope="col">Model</th>
                  <th scope="col">GSM8K base</th>
                  <th scope="col">GSM8K profile</th>
                  <th scope="col">CSQA base</th>
                  <th scope="col">CSQA profile</th>
                  <th scope="col">MMLU base</th>
                  <th scope="col">MMLU profile</th>
                </tr>
              </thead>
              <tbody>
                {benchmarks.map((row) => (
                  <tr key={row.model}>
                    <th scope="row">{row.model}</th>
                    <td>{row.gsm8k_base.toFixed(1)}</td>
                    <td>{row.gsm8k_profile.toFixed(1)}</td>
                    <td>{row.csqa_base.toFixed(1)}</td>
                    <td>{row.csqa_profile.toFixed(1)}</td>
                    <td>{row.mmlu_base.toFixed(1)}</td>
                    <td>{row.mmlu_profile.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="panel">
        <h2>This repo&apos;s 8-item run</h2>
        <p>
          Same 2×2 design and metrics, tiny seed set. Hosted Qwen3.5-4B was
          blocked here, so answers come from a mock policy that reproduces the
          paper&apos;s failure modes.
        </p>
        <ul className="takeaways">
          {DATA.takeaways.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <MiniBars />
        <p className="note">{DATA.notes[0]}</p>
      </section>

      <section className="panel">
        <h2>Prompt lab</h2>
        <p>
          Pick a seed item and a setting. The prompt is the actual string the
          pipeline would send. Edit the response to see the heuristic judge
          move.
        </p>
        <Playground />
      </section>

      <footer>
        Paper:{" "}
        <a href="https://arxiv.org/abs/2608.28833">arXiv:2608.28833</a>
        {" · "}
        Original code:{" "}
        <a href="https://github.com/yumeng-10/personalization_risk">
          yumeng-10/personalization_risk
        </a>
        {" · "}
        Replication generated {DATA.generated_at_utc.slice(0, 10)}.
      </footer>
    </main>
  );
}
