"use client";

import Link from "next/link";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, PieChart, Pie, Legend } from "recharts";
import { useAnalysis } from "@/lib/store";
import { Panel, scoreHex } from "@/components/ui";
import { FileCode2, Plus } from "lucide-react";

const AXIS = { fontSize: 11, fill: "#64748b" };
const TIP = { background: "#0b0f18", border: "1px solid #1e2434", borderRadius: 8, fontSize: 12 };

function Card({ title, children, sub }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <Panel className="p-5">
      <div className="text-sm font-medium text-slate-200">{title}</div>
      {sub && <div className="text-xs text-slate-500 mb-3">{sub}</div>}
      <div className="h-64 mt-2">{children}</div>
    </Panel>
  );
}

export default function MetricsPage() {
  const { current } = useAnalysis();
  if (!current) {
    return (
      <div className="p-6 sm:p-8 max-w-3xl mx-auto">
        <Panel className="p-10 text-center">
          <FileCode2 className="mx-auto text-slate-600 mb-4" size={32} />
          <div className="text-slate-200 font-medium mb-1">No analysis to show</div>
          <div className="text-slate-500 text-sm mb-5">Run an analysis first.</div>
          <Link href="/dashboard/analyze" className="inline-flex items-center gap-2 bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 rounded-lg px-4 py-2 text-sm">New Analysis <Plus size={14} /></Link>
        </Panel>
      </div>
    );
  }
  const fn = current.functions.map((f) => ({ name: f.name, health: f.health_score, complexity: f.complexity, cognitive: f.cognitive, nesting: f.nesting_depth, lines: f.lines }));
  const radar = current.factors.map((f) => ({ factor: f.label, score: f.score }));
  const byFactor = current.factors.filter((f) => f.findings > 0).map((f) => ({ name: f.label, findings: f.findings }));
  const sev = [
    { name: "critical", value: current.summary.critical, fill: "#ef4444" },
    { name: "warning", value: current.summary.warning, fill: "#f59e0b" },
    { name: "info", value: current.summary.info, fill: "#38bdf8" },
  ].filter((x) => x.value > 0);

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-50 mb-1">Metrics</h1>
      <p className="text-slate-500 text-sm mb-6 mono">{current.filename}</p>
      <div className="grid lg:grid-cols-2 gap-5">
        <Card title="Factor profile" sub="Line-weighted score per factor (100 = clean)">
          <ResponsiveContainer>
            <RadarChart data={radar} outerRadius="72%">
              <PolarGrid stroke="#1e2434" />
              <PolarAngleAxis dataKey="factor" tick={{ ...AXIS, fontSize: 10 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar dataKey="score" stroke="#22d3ee" fill="#22d3ee" fillOpacity={0.25} />
              <Tooltip contentStyle={TIP} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Health per function" sub="Below 50 is critical">
          <ResponsiveContainer>
            <BarChart data={fn} layout="vertical" margin={{ left: 40 }}>
              <CartesianGrid stroke="#1a2033" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={AXIS} />
              <YAxis type="category" dataKey="name" tick={AXIS} width={140} />
              <Tooltip contentStyle={TIP} />
              <Bar dataKey="health" radius={4}>{fn.map((f) => (<Cell key={f.name} fill={scoreHex(f.health)} />))}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Complexity per function" sub="Cyclomatic vs cognitive vs nesting">
          <ResponsiveContainer>
            <BarChart data={fn}>
              <CartesianGrid stroke="#1a2033" vertical={false} />
              <XAxis dataKey="name" tick={{ ...AXIS, fontSize: 9 }} interval={0} angle={-25} textAnchor="end" height={60} />
              <YAxis tick={AXIS} />
              <Tooltip contentStyle={TIP} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="complexity" fill="#22d3ee" radius={3} />
              <Bar dataKey="cognitive" fill="#a78bfa" radius={3} />
              <Bar dataKey="nesting" fill="#f59e0b" radius={3} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Function length" sub="Lines per function">
          <ResponsiveContainer>
            <BarChart data={fn}>
              <CartesianGrid stroke="#1a2033" vertical={false} />
              <XAxis dataKey="name" tick={{ ...AXIS, fontSize: 9 }} interval={0} angle={-25} textAnchor="end" height={60} />
              <YAxis tick={AXIS} />
              <Tooltip contentStyle={TIP} />
              <Bar dataKey="lines" fill="#38bdf8" radius={3} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Findings by factor">
          <ResponsiveContainer>
            <BarChart data={byFactor}>
              <CartesianGrid stroke="#1a2033" vertical={false} />
              <XAxis dataKey="name" tick={{ ...AXIS, fontSize: 9 }} interval={0} angle={-25} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} tick={AXIS} />
              <Tooltip contentStyle={TIP} />
              <Bar dataKey="findings" fill="#f59e0b" radius={3} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Findings by severity">
          <ResponsiveContainer>
            <PieChart>
              <Pie data={sev} dataKey="value" nameKey="name" outerRadius="75%" label />
              <Tooltip contentStyle={TIP} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
