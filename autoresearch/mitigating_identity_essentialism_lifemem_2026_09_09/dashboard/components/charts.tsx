"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { METHOD_LABELS, PAPER_METHODS, SES_COLORS, type DashboardData } from "@/lib/types";

const AXIS = { fill: "#b7ae98", fontSize: 12 };
const GRID = { stroke: "#3a3428", strokeDasharray: "3 6" };

export function PaperMetricChart({
  data,
  model,
  dataset,
  metric,
}: {
  data: DashboardData;
  model: string;
  dataset: "ah" | "us";
  metric: "kl" | "wg" | "ent" | "js";
}) {
  const key =
    metric === "js"
      ? "us_js"
      : `${dataset}_${metric === "ent" ? "ent" : metric === "wg" ? "wg" : "kl"}`;
  const rows = PAPER_METHODS.map((method) => ({
    method,
    value: data.paper.table1[model]?.[method]?.[key] ?? 0,
  }));
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="method" tick={AXIS} interval={0} angle={-28} textAnchor="end" height={70} />
        <YAxis tick={AXIS} />
        <Tooltip
          contentStyle={{ background: "#17140f", border: "1px solid #3a3428", color: "#efe6d2" }}
        />
        <Bar
          dataKey="value"
          fill="#7eafd4"
          radius={[6, 6, 0, 0]}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ReplicationChart({
  data,
  metric,
  methods,
}: {
  data: DashboardData;
  metric: string;
  methods?: DashboardData["replication"]["methods"];
}) {
  const rows = Object.entries(methods ?? data.replication.methods).map(([method, row]) => ({
    method: METHOD_LABELS[method] ?? method,
    value: Number(row[metric as keyof typeof row] ?? 0),
    fill: method === "lifemem" ? "#7eafd4" : method === "profile" ? "#d06a4f" : "#c2b8a3",
  }));
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="method" tick={AXIS} interval={0} angle={-28} textAnchor="end" height={70} />
        <YAxis tick={AXIS} />
        <Tooltip
          contentStyle={{ background: "#17140f", border: "1px solid #3a3428", color: "#efe6d2" }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} isAnimationActive={false}>
          {rows.map((row) => (
            <Cell key={row.method} fill={row.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LatencyChart({ data }: { data: DashboardData }) {
  const rows = Object.keys(data.paper.latency_ms["Add Health"]).map((method) => ({
    method,
    "Add Health": data.paper.latency_ms["Add Health"][method],
    "Understanding Society": data.paper.latency_ms["Understanding Society"][method],
  }));
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="method" tick={AXIS} interval={0} angle={-28} textAnchor="end" height={70} />
        <YAxis tick={AXIS} />
        <Legend />
        <Tooltip
          contentStyle={{ background: "#17140f", border: "1px solid #3a3428", color: "#efe6d2" }}
        />
        <Bar dataKey="Add Health" fill="#e2b657" radius={[6, 6, 0, 0]} isAnimationActive={false} />
        <Bar
          dataKey="Understanding Society"
          fill="#7eafd4"
          radius={[6, 6, 0, 0]}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function SweepChart({
  rows,
  xKey,
}: {
  rows: { kl: number; wg: number; ent: number; [key: string]: number }[];
  xKey: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey={xKey} tick={AXIS} />
        <YAxis tick={AXIS} />
        <Legend />
        <Tooltip
          contentStyle={{ background: "#17140f", border: "1px solid #3a3428", color: "#efe6d2" }}
        />
        <Line type="monotone" dataKey="kl" stroke="#7eafd4" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="wg" stroke="#e2b657" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="ent" stroke="#d06a4f" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function IdentityScatter({
  cloud,
  title,
}: {
  cloud: DashboardData["replication"]["identity"][string];
  title: string;
}) {
  const groups = ["low", "middle", "high"];
  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="text-xl">{title}</h3>
        <p className="text-sm text-[var(--muted)]">
          silhouette {cloud.silhouette.toFixed(3)}
        </p>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid {...GRID} />
          <XAxis type="number" dataKey="x" tick={AXIS} name="PC1" />
          <YAxis type="number" dataKey="y" tick={AXIS} name="PC2" />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            contentStyle={{ background: "#17140f", border: "1px solid #3a3428", color: "#efe6d2" }}
          />
          {groups.map((ses) => (
            <Scatter
              key={ses}
              name={ses}
              data={cloud.points.filter((point) => point.ses === ses)}
              fill={SES_COLORS[ses]}
              isAnimationActive={false}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

export function AdapterScatter({ data }: { data: DashboardData }) {
  const waves = [...new Set(data.replication.adapter_pca.points.map((p) => p.wave ?? 0))];
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
        <CartesianGrid {...GRID} />
        <XAxis type="number" dataKey="x" tick={AXIS} />
        <YAxis type="number" dataKey="y" tick={AXIS} />
        <Legend />
        <Tooltip
          contentStyle={{ background: "#17140f", border: "1px solid #3a3428", color: "#efe6d2" }}
        />
        {waves.map((wave) => (
          <Scatter
            key={wave}
            name={`wave ${wave}`}
            data={data.replication.adapter_pca.points.filter((p) => p.wave === wave)}
            fill={`hsl(${28 + wave * 28} 62% 62%)`}
            isAnimationActive={false}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}
