"use client";

import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import paper from "@/public/data/paper_results.json";
import mini from "@/public/data/mini_replication.json";

const tooltipStyle = {
  backgroundColor: "#14120e",
  border: "1px solid #2b261f",
  borderRadius: 8,
  color: "#f3eadc",
};

export function Charts() {
  const layerData = paper.layer_sweep_reconstructed.map((row) => ({
    layer: row.layer,
    "α=0.1": row.a01,
    "α=0.2": row.a02,
    "α=0.3": row.a03,
  }));

  const disengageData = paper.table2_disengagement.slice(0, 4).map((row) => ({
    alpha: row.condition.includes("Unsteered")
      ? "0.0"
      : (row.condition.match(/alpha=([0-9.]+)/)?.[1] ?? row.condition),
    "Disengage %": Number((row.rate * 100).toFixed(1)),
    "Exact match %": Number((row.exact * 100).toFixed(1)),
  }));

  const profileTradeoff = paper.table5_profile_tradeoff.writing_style_profile.map(
    (row, index) => ({
      alpha: row.alpha,
      "Writing profile": row.overall,
      "Interaction profile":
        paper.table5_profile_tradeoff.interaction_style_profile[index]?.overall,
    }),
  );

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard
        title="User-likeness by layer"
        note="Layers 10–14 are from Table 10. Other layers are a reconstruction of Figure 4’s mid-layer peak."
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={layerData}>
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="layer" stroke="#b7ab98" />
            <YAxis domain={[1, 4]} stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Line type="monotone" dataKey="α=0.1" stroke="#b7ab98" dot={false} />
            <Line type="monotone" dataKey="α=0.2" stroke="#7ec8c0" dot={false} />
            <Line type="monotone" dataKey="α=0.3" stroke="#d9772c" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Disengagement vs steering"
        note="Table 2, Qwen 3.5 9B. Exact match peaks at 5.9% when α=0.2, then the simulator leaves too early."
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={disengageData}>
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="alpha" stroke="#b7ab98" />
            <YAxis stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Line
              type="monotone"
              dataKey="Disengage %"
              stroke="#d9772c"
            />
            <Line
              type="monotone"
              dataKey="Exact match %"
              stroke="#7ec8c0"
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="SimulatorArena similarity"
        note="Table 3, zero-shot Qwen. Writing style rises; interaction style barely moves."
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={paper.table3_simulator_arena.slice(0, 4)}>
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="condition" stroke="#b7ab98" tick={{ fontSize: 11 }} />
            <YAxis domain={[1, 4]} stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Bar dataKey="writing" fill="#d9772c" />
            <Bar dataKey="interaction" fill="#7ec8c0" />
            <Bar dataKey="overall" fill="#f3eadc" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Behavior exaggeration"
        note="Table 4. At α=0.3, doubt and mistake rates pass the human ground truth."
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={paper.table4_behavior_rates}>
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="condition" stroke="#b7ab98" tick={{ fontSize: 11 }} />
            <YAxis stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Bar dataKey="doubt" fill="#d9772c" />
            <Bar dataKey="mistake" fill="#e07060" />
            <Bar dataKey="misunderstanding" fill="#7ec8c0" />
            <Bar dataKey="question" fill="#f3eadc" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Trait cosine with the user vector"
        note="Figure 7 is not published as numbers. These values reconstruct the paper’s ranking: most assistant traits point away from the user direction."
      >
        <ResponsiveContainer width="100%" height={360}>
          <BarChart
            data={paper.trait_cosine_reconstructed}
            layout="vertical"
            margin={{ left: 88 }}
          >
            <CartesianGrid stroke="#2b261f" />
            <XAxis type="number" stroke="#b7ab98" />
            <YAxis type="category" dataKey="trait" stroke="#b7ab98" width={80} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="cosine" fill="#d9772c" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="User-role activation across turns"
        note="Figure 8 reconstructed. Activation falls as the conversation gets longer."
      >
        <ResponsiveContainer width="100%" height={360}>
          <LineChart data={paper.turn_activation}>
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="turn" stroke="#b7ab98" />
            <YAxis stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Line dataKey="goal_only" stroke="#f3eadc" dot={false} />
            <Line dataKey="demographics" stroke="#d9772c" dot={false} />
            <Line dataKey="linguistic" stroke="#7ec8c0" dot={false} />
            <Line dataKey="full" stroke="#b7ab98" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Mini-replication: planted direction recovery"
        note={`CPU run with 48 synthetic dialogues. Recovered cosine with the planted user direction is ${mini.recovery_cosine.toFixed(3)}.`}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={Object.entries(mini.steered_projection).map(([alpha, value]) => ({
              alpha,
              projection: value,
            }))}
          >
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="alpha" stroke="#b7ab98" />
            <YAxis stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="projection" fill="#7ec8c0" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="User-likeness at layer 11"
        note="Table 1. Steering α=0.3 toward the user direction raises mean likeness from 1.51 to 3.76; the assistant direction drops it to 1.05."
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={paper.table1_style_layer11}>
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="direction" stroke="#b7ab98" />
            <YAxis domain={[1, 5]} stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Bar dataKey="brevity" fill="#d9772c" />
            <Bar dataKey="informality" fill="#e07060" />
            <Bar dataKey="pacing" fill="#7ec8c0" />
            <Bar dataKey="mean" fill="#f3eadc" />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Profile trade-off"
        note="Table 5. Once a person-specific profile is in the prompt, stronger steering lowers overall similarity."
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={profileTradeoff}>
            <CartesianGrid stroke="#2b261f" />
            <XAxis dataKey="alpha" stroke="#b7ab98" />
            <YAxis domain={[2.8, 3.6]} stroke="#b7ab98" />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <Line dataKey="Writing profile" stroke="#d9772c" />
            <Line dataKey="Interaction profile" stroke="#7ec8c0" />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

function ChartCard({
  title,
  note,
  children,
}: {
  title: string;
  note: string;
  children: ReactNode;
}) {
  return (
    <section className="panel p-4 md:p-5">
      <h3 className="text-xl">{title}</h3>
      <p className="mt-1 mb-4 text-sm text-[var(--muted)]">{note}</p>
      {children}
    </section>
  );
}
