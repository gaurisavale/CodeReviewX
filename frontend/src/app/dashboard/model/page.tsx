"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchModel } from "@/lib/api";
import { ModelDetail } from "@/lib/types";
import { Panel } from "@/components/ui";

export default function ModelPage() {
  const [m, setM] = useState<ModelDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { fetchModel().then(setM).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="p-8 text-red-400 text-sm">{err}</div>;
  if (!m) return <div className="p-8 text-slate-500 text-sm">Loading model card...</div>;

  const cmp = Object.entries(m.comparison).map(([name, v]) => ({ name, auc: v.auc }));
  const factors = Object.keys(m.hand_weights);

  return (
    <div className="p-6 sm:p-8 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-50">Defect-risk model</h1>
        <p className="text-slate-500 text-sm mt-1">A logistic regression trained on real bug-fix history. It ranks which functions are most likely to need a later fix. Every prediction decomposes into per-feature contributions.</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {[["Training functions", m.functions.toLocaleString()], ["Defective", `${m.defective.toLocaleString()} (${(m.base_rate * 100).toFixed(1)}%)`], ["Repositories", m.repos], ["Held-out AUC", `${m.auc} ± ${m.auc_std}`], ["Recall at top 20%", `${(m.recall_at_20 * 100).toFixed(0)}%`]].map(([k, v]) => (
          <Panel key={String(k)} className="p-4"><div className="text-[11px] uppercase text-slate-500">{k}</div><div className="text-lg font-semibold text-slate-50">{v}</div></Panel>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <Panel className="p-5">
          <div className="text-sm font-semibold text-slate-100 mb-1">Model comparison (leave-one-repository-out AUC)</div>
          <div className="text-xs text-slate-500 mb-3">Each repo is held out in turn. 0.5 is chance.</div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cmp} layout="vertical" margin={{ left: 150 }}>
                <CartesianGrid stroke="#1e293b" horizontal={false} />
                <XAxis type="number" domain={[0.4, 0.8]} stroke="#64748b" fontSize={11} />
                <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={10} width={150} />
                <Tooltip contentStyle={{ background: "#0b1020", border: "1px solid #1e293b", fontSize: 11 }} />
                <Bar dataKey="auc" radius={3}>{cmp.map((d) => <Cell key={d.name} fill={d.name === m.name ? "#22d3ee" : "#475569"} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel className="p-5">
          <div className="text-sm font-semibold text-slate-100 mb-3">Strongest learned effects (standardised weights)</div>
          <div className="space-y-1.5">
            {m.coefficients.slice(0, 10).map((c) => (
              <div key={c.feature} className="flex items-center gap-2 text-[11px]">
                <span className="w-32 text-slate-400 mono">{c.feature}</span>
                <div className="flex-1 h-2 rounded bg-slate-800 relative"><div className="absolute h-2 rounded" style={{ left: c.weight >= 0 ? "50%" : `${50 + c.weight * 80}%`, width: `${Math.abs(c.weight) * 80}%`, background: c.weight >= 0 ? "#ef4444" : "#10b981" }} /></div>
                <span className="w-10 text-right text-slate-300">{c.weight.toFixed(2)}</span>
              </div>
            ))}
          </div>
          <div className="text-[10px] text-slate-600 mt-2">Red raises risk, green lowers it. Features overlap, so read them together.</div>
        </Panel>
      </div>

      <Panel className="p-5">
        <div className="text-sm font-semibold text-slate-100 mb-3">Hand-set vs data-calibrated factor weights</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-xs">
          {factors.map((k) => (
            <div key={k} className="rounded-lg border border-slate-800 bg-slate-900/40 p-2">
              <div className="text-slate-400">{k.replace("_", " ")}</div>
              <div className="text-slate-200 mono">{m.hand_weights[k]} → <span className="text-cyan-300">{m.learned_weights[k]}</span></div>
            </div>
          ))}
        </div>
        <div className="text-[10px] text-slate-600 mt-2">Learned weights come from a regression on the 13 factor scores. Enable them with CODEREVIEWX_USE_LEARNED_WEIGHTS=true.</div>
      </Panel>

      <Panel className="p-5">
        <div className="text-sm font-semibold text-slate-100 mb-2">Training data and caveats</div>
        <p className="text-sm text-slate-400 mb-2">{m.label_definition}</p>
        <div className="text-xs text-slate-500 mb-2">Repositories: {Object.entries(m.per_repo).map(([r, v]) => `${r} (${v.functions.toLocaleString()})`).join(", ")}</div>
        <ul className="list-disc pl-5 text-xs text-slate-500 space-y-1">{m.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
      </Panel>
    </div>
  );
}
