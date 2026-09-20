"use client";

import { useMemo, useState } from "react";
import type {
  DashboardData,
  QuestionRow,
  Room,
} from "./types";

const AXIS_LABEL: Record<string, string> = {
  sex: "Sex",
  age_env: "Age",
  age_birth: "Age",
  education: "Education",
  region: "Region",
  marital: "Marital status",
};

function axesForQuestion(question: QuestionRow | undefined): string[] {
  if (!question) return [];
  const seen: string[] = [];
  for (const row of question.groups) {
    if (!seen.includes(row.axis)) {
      seen.push(row.axis);
    }
  }
  return seen;
}

const CONTROL_LABEL: Record<string, string> = {
  full: "Full persona",
  demographics: "Demographics only",
  citizen: "Citizen prompt",
  none: "No persona",
};

function pct(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(digits)}%`;
}

function pts(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(1)} pts`;
}

function agents(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(1)} / 6`;
}

function heatColor(share: number): string {
  const t = Math.max(0, Math.min(100, share)) / 100;
  const r = Math.round(157 + (28 - 157) * t);
  const g = Math.round(43 + (75 - 43) * t);
  const b = Math.round(22 + (90 - 22) * t);
  return `rgba(${r}, ${g}, ${b}, 0.28)`;
}

function Bar({
  share,
  color,
  label,
}: {
  share: number | null | undefined;
  color: string;
  label: string;
}) {
  const width = share == null ? 0 : Math.max(2, Math.min(100, share));
  return (
    <div className="bar-row">
      <span>{label}</span>
      <div className="bar-track" aria-hidden="true">
        {share == null ? null : (
          <div className="bar-fill" style={{ width: `${width}%`, background: color }} />
        )}
      </div>
      <strong>{pct(share, 1)}</strong>
    </div>
  );
}

function liveForQuestion(data: DashboardData, questionId: string) {
  return data.survey.live_qwen_sample.find((row) => row.question_id === questionId);
}

function liveSampleN(data: DashboardData): number {
  return data.survey.live_qwen_sample.reduce((sum, row) => sum + row.n, 0);
}

function roomTitle(room: Room): string {
  return `${room.question_id}, ${room.protocol}, ${room.start_composition}`;
}

export function Dashboard({ data }: { data: DashboardData }) {
  const questions = data.survey.questions;
  const [qid, setQid] = useState(questions[0]?.id ?? "env_priority");
  const [_axis, setAxis] = useState<string | undefined>(undefined);
  const [roomId, setRoomId] = useState(data.deliberation.rooms[0]?.room_id ?? "");
  const question = questions.find((row) => row.id === qid) ?? questions[0];
  const questionAxes = useMemo(() => axesForQuestion(question), [question]);
  const axis =
    _axis && questionAxes.includes(_axis) ? _axis : (questionAxes[0] ?? "sex");
  const live = liveForQuestion(data, qid);
  const offline = data.replication.offline;
  const runName = offline ? "Dummy run" : "Qwen run";
  const showLiveSample = offline && liveSampleN(data) > 0;
  const questionControls = data.survey.controls.filter(
    (row) => row.question_id === qid && row.n > 0,
  );
  const room = data.deliberation.rooms.find((item) => item.room_id === roomId)
    ?? data.deliberation.rooms[0];
  const table3Questions = Object.keys(data.paper.table3);
  const groupRows = useMemo(() => {
    if (!question) return [];
    return question.groups.filter((row) => row.axis === axis);
  }, [question, axis]);
  const paperGroups = useMemo(() => {
    if (!question) return [];
    return question.paper_groups.filter((row) => row.axis === axis);
  }, [question, axis]);

  return (
    <div className="page">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="masthead">
        <span>Jang, Kim, Cha, and Cha</span>
        <span className="kicker">arXiv 2609.07573</span>
      </header>
      <h1>From simulated citizens to simulated deliberation</h1>
      <p className="lede">
        Census-balanced LLM personas are asked eight Korean policy questions, then
        six of them debate for three rounds. The paper finds that those answers
        miss the human survey map, and that stance movement still happens when
        agents cannot hear one another. The charts on this page compare the
        paper&apos;s GPT-4.1-mini numbers with a live Qwen 3.5 4B run on{" "}
        {data.replication.n_personas} personas spread across{" "}
        {data.replication.cells} demographic cells.
      </p>
      <div className="conditions">
        <div className="stamp">
          <span>Paper, GPT-4.1-mini, 640 personas</span>
          <strong>{pts(29)}</strong>
          mean absolute group gap
          <span className="verdict">Misses humans</span>
        </div>
        <div className="stamp">
          <span>
            {data.replication.model}, {data.replication.n_personas} personas
          </span>
          <strong>{pts(data.survey.mean_group_gap)}</strong>
          mean absolute group gap
          <span className="verdict">{offline ? "Offline dummy" : "Live Qwen"}</span>
        </div>
      </div>
      <aside className="banner">{data.replication.note}</aside>

      <main id="main">
        <section>
          <h2>Takeaways</h2>
          <p className="section-help">
            The first block is what Jang et al. reported. The second block is
            what this folder actually ran.
          </p>
          <div className="takeaways">
            {data.paper.findings.map((item, index) => (
              <article className="takeaway" key={`paper-${item.id}`}>
                <div className="num">{String(index + 1).padStart(2, "0")}</div>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
          <h3 className="subhead">This folder</h3>
          <div className="takeaways">
            {data.takeaways.map((item) => (
              <article className="takeaway" key={`run-${item.id}`}>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section>
          <h2>Position A share by question</h2>
          <p className="section-help">
            Position A is the paper&apos;s first coded option, not whichever option
            was shown first. Display order is randomized. Click a question to
            inspect group splits.
          </p>
          <div className="legend">
            <span>
              <i className="swatch" style={{ background: "var(--human)" }} />
              Human survey
            </span>
            <span>
              <i className="swatch" style={{ background: "var(--gpt)" }} />
              Paper GPT-4.1-mini
            </span>
            <span>
              <i className="swatch" style={{ background: "var(--run)" }} />
              {runName}
            </span>
            {showLiveSample ? (
              <span>
                <i className="swatch" style={{ background: "var(--qwen)" }} />
                Live Qwen sample
              </span>
            ) : null}
          </div>
          <div className="questions" role="tablist" aria-label="Policy questions">
            {questions.map((row) => (
              <button
                key={row.id}
                type="button"
                role="tab"
                aria-selected={row.id === qid}
                aria-pressed={row.id === qid}
                onClick={() => setQid(row.id)}
              >
                {row.topic_en}
              </button>
            ))}
          </div>
          {question ? (
            <QuestionBars
              row={question}
              liveShare={showLiveSample ? live?.persona_share : null}
              runLabel={runName}
            />
          ) : null}
        </section>

        {question ? (
          <section>
            <h2>{question.topic_en}</h2>
            <p className="section-help">
              {question.topic_ko}. {runName} Position A is{" "}
              {pct(question.persona_overall, 1)} (n={data.replication.n_personas}).
              Human: {pct(question.human_overall)}. Paper GPT:{" "}
              {pct(question.paper_gpt41mini)}.
            </p>
            <div className="positions">
              <div className="pos a">
                <span>Position A</span>
                {question.position_a_en}
                <em> {question.position_a_ko}</em>
              </div>
              <div className="pos b">
                <span>Position B</span>
                {question.position_b_en}
                <em> {question.position_b_ko}</em>
              </div>
            </div>
            <div className="axis-tabs" role="tablist" aria-label="Demographic axis">
              {questionAxes.map((axisId) => (
                <button
                  key={axisId}
                  type="button"
                  role="tab"
                  aria-pressed={axis === axisId}
                  onClick={() => setAxis(axisId)}
                >
                  {AXIS_LABEL[axisId] ?? axisId}
                </button>
              ))}
            </div>
            <table className="group-table">
              <thead>
                <tr>
                  <th>Group</th>
                  <th>{runName} A</th>
                  <th>Paper GPT A</th>
                  <th>Human A</th>
                  <th>n</th>
                  <th>Gap</th>
                </tr>
              </thead>
              <tbody>
                {groupRows.map((row) => {
                  const paper = paperGroups.find((item) => item.group === row.group);
                  const gap =
                    row.persona_share == null
                      ? null
                      : Math.abs(row.persona_share - row.human_share);
                  return (
                    <tr key={`${row.axis}-${row.group}`}>
                      <td>{row.group}</td>
                      <td>{pct(row.persona_share, 1)}</td>
                      <td>{pct(paper?.persona_share)}</td>
                      <td>{pct(row.human_share)}</td>
                      <td>{row.n}</td>
                      <td>
                        <span className="tiny-bars" aria-hidden="true">
                          <i
                            style={{
                              width: `${row.persona_share ?? 0}%`,
                              background: "var(--run)",
                            }}
                          />
                          <i
                            style={{
                              width: `${row.human_share}%`,
                              background: "var(--human)",
                            }}
                          />
                        </span>
                        {pts(gap)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ) : null}

        <section>
          <h2>Ablation overall A-share (paper Table 3)</h2>
          <p className="section-help">
            Full personas, demographics only, a generic citizen prompt, and no
            persona. Values are percent choosing Position A. Human is the survey
            benchmark.
          </p>
          <div className="heat">
            <div className="heat-row heat-head">
              <span />
              <span>Full</span>
              <span>Demographics</span>
              <span>Citizen</span>
              <span>None</span>
              <span>Human</span>
            </div>
            {table3Questions.map((id) => {
              const row = data.paper.table3[id];
              return (
                <div className="heat-row" key={id}>
                  <span>{id}</span>
                  {(["full", "demographics", "citizen", "none", "human"] as const).map(
                    (key) => (
                      <span
                        className="cell"
                        key={key}
                        style={{ background: heatColor(row[key]) }}
                      >
                        {row[key]}
                      </span>
                    ),
                  )}
                </div>
              );
            })}
          </div>
          {questionControls.length > 0 ? (
            <>
              <h3 className="subhead">Control conditions in this folder</h3>
              <table className="group-table">
                <thead>
                  <tr>
                    <th>Condition</th>
                    <th>Question</th>
                    <th>{runName} A</th>
                    <th>Human A</th>
                    <th>n</th>
                  </tr>
                </thead>
                <tbody>
                  {questionControls.map((row) => (
                    <tr key={`${row.condition}-${row.question_id}`}>
                      <td>{CONTROL_LABEL[row.condition] ?? row.condition}</td>
                      <td>{row.question_id}</td>
                      <td>{pct(row.persona_share, 1)}</td>
                      <td>{pct(row.human_overall)}</td>
                      <td>{row.n}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : null}
        </section>

        <section>
          <h2>Debate versus sealed monologue</h2>
          <p className="section-help">
            Paper Table 6 reports mean Position A counts after round 3 in balanced
            rooms of six. Table 7 reports how many agents later changed after a
            restated opening side.{" "}
            {offline
              ? "Rooms in this folder are dummy protocol walkthroughs."
              : `Rooms in this folder are live Qwen 3.5 4B transcripts on the ${data.replication.n_personas}-persona slice.`}
          </p>
          <div className="stats">
            <div className="stat">
              <b>{data.survey.direction_matches}/{data.survey.direction_total}</b>
              direction matches
            </div>
            <div className="stat">
              <b>{data.survey.near_unanimous_groups}</b>
              near-unanimous groups
            </div>
            <div className="stat">
              <b>{data.replication.n_rooms}</b>
              rooms
            </div>
            <div className="stat">
              <b>{data.replication.n_survey_full}</b>
              survey answers
            </div>
          </div>
          <table className="group-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Paper debate</th>
                <th>Paper monologue</th>
                <th>Paper gap</th>
                <th>{runName} debate</th>
                <th>{runName} monologue</th>
              </tr>
            </thead>
            <tbody>
              {data.paper.table6.map((row) => {
                const runRow = data.deliberation.debate_vs_monologue.find(
                  (item) => item.question_id === row.question_id,
                );
                return (
                  <tr key={String(row.question_id)}>
                    <td>{String(row.question_id)}</td>
                    <td>{agents(Number(row.debate_final_a))}</td>
                    <td>{agents(Number(row.monologue_final_a))}</td>
                    <td>{Number(row.difference).toFixed(1)}</td>
                    <td>{agents(runRow?.debate_final_a)}</td>
                    <td>{agents(runRow?.monologue_final_a)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <h3 className="subhead">Paper Table 7, share that moved after round 1</h3>
          <table className="group-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Open debate move</th>
                <th>Restated-side move</th>
                <th>Open debate final A</th>
                <th>Restated final A</th>
              </tr>
            </thead>
            <tbody>
              {data.paper.table7.map((row) => (
                <tr key={String(row.question_id)}>
                  <td>{String(row.question_id)}</td>
                  <td>{pct(Number(row.nothing_move))}</td>
                  <td>{pct(Number(row.restated_move))}</td>
                  <td>{agents(Number(row.nothing_a))}</td>
                  <td>{agents(Number(row.restated_a))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h2>Room explorer</h2>
          <p className="section-help">
            {data.replication.n_rooms} rooms cover climate technology and
            education care under debate, monologue, all A, all B, and
            restated-side protocols. Speakers are{" "}
            {offline ? "dummy protocol agents" : "the live Qwen agents"}.
          </p>
          <div className="room-layout">
            <div>
              <label htmlFor="room-select">Room</label>
              <select
                id="room-select"
                className="room-select"
                value={room?.room_id ?? ""}
                onChange={(event) => setRoomId(event.target.value)}
              >
                {data.deliberation.rooms.map((item) => (
                  <option key={item.room_id} value={item.room_id}>
                    {roomTitle(item)}
                  </option>
                ))}
              </select>
              {room ? (
                <>
                  <p className="counts">
                    A counts {room.a_counts.join(" → ")}
                    {room.movement == null
                      ? null
                      : `, moved ${(100 * room.movement).toFixed(0)}%`}
                  </p>
                  {room.agents.map((agent) => (
                    <div className="agent-card" key={agent.id}>
                      <strong>{agent.name}</strong>
                      <div>
                        {agent.sex ?? "n/a"}, {agent.age ?? "n/a"}, {agent.education ?? "n/a"},{" "}
                        {agent.region ?? "n/a"}, assigned {agent.assigned_side}
                      </div>
                      <div className="dots" aria-label="Stances by round">
                        {agent.stances.map((stance, index) => (
                          <span
                            className={`dot ${stance ?? ""}`}
                            key={`${agent.id}-${index}`}
                          >
                            {stance ?? "?"}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </>
              ) : null}
            </div>
            <div className="transcript">
              {room?.turns.map((turn, index) => (
                <article className="turn" key={`${turn.speaker_id}-${turn.round_index}-${index}`}>
                  <header>
                    Round {turn.round_index}, {turn.speaker_name}
                    {turn.visible_to.length <= 1 ? ", sealed" : ""}
                  </header>
                  <p>{turn.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {showLiveSample ? (
        <section>
          <h2>Earlier live Qwen sample</h2>
          <p className="section-help">
            A smaller full-condition sample kept next to an offline dummy run.
          </p>
          <table className="group-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Live Qwen A</th>
                <th>Paper GPT A</th>
                <th>Human A</th>
                <th>n</th>
              </tr>
            </thead>
            <tbody>
              {data.survey.live_qwen_sample.map((row) => (
                <tr key={row.question_id}>
                  <td>{row.question_id}</td>
                  <td>{pct(row.persona_share)}</td>
                  <td>{pct(row.paper_gpt41mini)}</td>
                  <td>{pct(row.human_overall)}</td>
                  <td>{row.n}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        ) : null}
      </main>

      <footer className="footer">
        <p>
          Paper:{" "}
          <a href={data.paper.url} target="_blank" rel="noreferrer">
            {data.paper.title}
          </a>
          . alphaXiv:{" "}
          <a href={data.paper.alphaxiv} target="_blank" rel="noreferrer">
            {data.paper.alphaxiv}
          </a>
          . Official code:{" "}
          <a
            href="https://github.com/jchaemin/simulated-deliberation"
            target="_blank"
            rel="noreferrer"
          >
            jchaemin/simulated-deliberation
          </a>
          . Personas are real draws from nvidia/Nemotron-Personas-Korea. Model on
          this page: {data.replication.model}.
        </p>
      </footer>
    </div>
  );
}

function QuestionBars({
  row,
  liveShare,
  runLabel,
}: {
  row: QuestionRow;
  liveShare: number | null | undefined;
  runLabel: string;
}) {
  return (
    <div className="bars">
      <Bar share={row.human_overall} color="var(--human)" label="Human survey" />
      <Bar share={row.paper_gpt41mini} color="var(--gpt)" label="Paper GPT-4.1-mini" />
      <Bar share={row.persona_overall} color="var(--run)" label={runLabel} />
      {liveShare == null ? null : (
        <Bar share={liveShare} color="var(--qwen)" label="Live Qwen sample" />
      )}
    </div>
  );
}
