"use client";

import { AnalyzeResponse } from "@/lib/types";
import { Panel, ProgressBar, scoreColorClass, scoreHex, scoreTextColor } from "./ui";
import { Brain, Cpu, GitBranch, Package, Target } from "lucide-react";

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div title={hint} className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-slate-100 font-semibold mono">{value}</div>
    </div>
  );
}

export default function OverviewPanel({ result, onPickIssue }: { result: AnalyzeResponse; onPickIssue: (id: string) => void }) {
  const s = result.summary;
  const ex = result.explanation;
  const color = scoreHex(s.overall_health);
  const weakest = [...result.factors].sort((a, b) => a.score - b.score).filter((f) => f.score < 90).slice(0, 4);
  return (
    <div className="grid lg:grid-cols-[320px_1fr] gap-5">
      <Panel className="p-5">
        <div className="flex items-center gap-4">
          <div
            className="w-24 h-24 rounded-full grid place-items-center shrink-0"
            style={{ background: `conic-gradient(${color} ${s.overall_health * 3.6}deg, #1e2434 0deg)` }}
          >
            <div className="w-[84px] h-[84px] rounded-full bg-[#0a0d16] grid place-items-center">
              <div className="text-center">
                <div className="text-2xl font-semibold" style={{ color }}>{s.overall_health}</div>
                <div className="text-[10px] text-slate-500">Grade {s.grade}</div>
              </div>
            </div>
          </div>
          <div className="text-sm text-slate-300 leading-snug">{s.verdict}</div>
        </div>
        <div className="grid grid-cols-3 gap-2 mt-5 text-center text-xs">
          <div className="rounded-lg bg-red-500/10 border border-red-500/30 py-2"><div className="text-lg font-semibold text-red-400">{s.critical}</div>critical</div>
          <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 py-2"><div className="text-lg font-semibold text-amber-400">{s.warning}</div>warning</div>
          <div className="rounded-lg bg-sky-500/10 border border-sky-500/30 py-2"><div className="text-lg font-semibold text-sky-300">{s.info}</div>info</div>
        </div>
        <div className="mt-5 space-y-2.5">
          {Object.entries(result.categories).map(([k, v]) => (
            <div key={k}>
              <div className="flex justify-between text-xs mb-1"><span className="capitalize text-slate-400">{k}</span><span className={scoreTextColor(v)}>{v}</span></div>
              <ProgressBar value={v} colorClass={scoreColorClass(v)} />
            </div>
          ))}
        </div>
      </Panel>

      <div className="space-y-5">
        <Panel className="p-5">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-2"><Target size={15} className="text-cyan-400" /> What this code does</div>
          <p className="text-sm text-slate-300 leading-relaxed">{ex.purpose}</p>
          {ex.overview.entry_points.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-slate-400">
              <GitBranch size={13} /> Entry points:
              {ex.overview.entry_points.slice(0, 6).map((e) => (<span key={e} className="mono px-2 py-0.5 rounded bg-slate-800 text-slate-200">{e}()</span>))}
            </div>
          )}
          {s.imports.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-slate-400">
              <Package size={13} /> Imports:
              {s.imports.map((e) => (<span key={e} className="mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">{e}</span>))}
            </div>
          )}
        </Panel>

        <Panel className="p-5">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3"><Brain size={15} className="text-purple-400" /> Why it scored this way</div>
          <p className="text-sm text-slate-300 leading-relaxed">{ex.why}</p>
          {weakest.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {weakest.map((f) => (
                <span key={f.key} className="text-xs px-2 py-1 rounded-full border border-slate-700 text-slate-300">
                  {f.label} <b style={{ color: scoreHex(f.score) }}>{f.score}</b>
                </span>
              ))}
            </div>
          )}
          <div className="mt-4 text-xs uppercase tracking-wide text-slate-500">Fix first</div>
          <ol className="mt-2 space-y-1.5">
            {ex.priorities.slice(0, 5).map((p, i) => (
              <li key={p.id}>
                <button onClick={() => onPickIssue(p.id)} className="text-left text-sm text-slate-200 hover:text-cyan-300">
                  <span className="text-slate-500 mr-2">{i + 1}.</span>{p.title} <span className="text-slate-500 mono">in {p.function}()</span>
                </button>
              </li>
            ))}
          </ol>
          <div className="mt-3 text-sm text-slate-400">{ex.recommendation}</div>
        </Panel>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <Stat label="Lines" value={`${s.total_lines}`} hint={`${s.code_lines} code, ${s.comment_lines} comments, ${s.blank_lines} blank`} />
          <Stat label="Functions" value={s.functions} />
          <Stat label="Avg / Max Cx" value={`${s.avg_complexity} / ${s.max_complexity}`} hint="Cyclomatic complexity" />
          <Stat label="Cognitive total" value={s.total_cognitive} />
          <Stat label="Max nesting" value={s.max_nesting_depth} hint="elif is not counted as nesting" />
          <Stat label="Avg / Max length" value={`${s.average_function_length} / ${s.max_function_length}`} />
          <Stat label="Maintainability" value={`${s.maintainability_score}%`} />
          <Stat label="Worst function" value={s.worst_function ?? "-"} />
          {s.defect_risk_high !== undefined && (
            <Stat label="High bug-risk fns" value={`${s.defect_risk_high} / ${s.functions}`} hint={`Trained model. Riskiest: ${s.riskiest_function ?? "-"}`} />
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Cpu size={13} /> Numbers: structural analyzer (deterministic). Explanations: {ex.source === "claude" ? `Claude (${ex.model})` : "built-in rule explainer (no API key)"}.
        </div>
      </div>
    </div>
  );
}
