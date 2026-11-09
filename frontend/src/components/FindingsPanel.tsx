"use client";

import { useMemo, useState } from "react";
import clsx from "clsx";
import { AnalyzeResponse, Severity } from "@/lib/types";
import FactorHint from "./FactorHint";
import { Panel, SeverityBadge } from "./ui";
import { Wand2, Crosshair } from "lucide-react";

const SEVS: (Severity | "all")[] = ["all", "critical", "warning", "info"];

export default function FindingsPanel({
  result,
  selectedFunction,
  factor,
  activeIssueId,
  onFactor,
  onPick,
}: {
  result: AnalyzeResponse;
  selectedFunction: string | null;
  factor: string | null;
  activeIssueId: string | null;
  onFactor: (f: string | null) => void;
  onPick: (id: string, fn: string) => void;
}) {
  const [sev, setSev] = useState<Severity | "all">("all");
  const [scope, setScope] = useState<"all" | "function">("all");
  const labels = useMemo(() => Object.fromEntries(result.factors.map((f) => [f.key, f.label])), [result.factors]);
  const list = result.issues.filter(
    (i) => (sev === "all" || i.severity === sev) && (!factor || i.factor === factor) && (scope === "all" || i.function === selectedFunction)
  );
  const factorsWithIssues = result.factors.filter((f) => f.findings > 0);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {SEVS.map((s) => (
          <button
            key={s}
            onClick={() => setSev(s)}
            className={clsx("text-xs px-3 py-1 rounded-full border capitalize", sev === s ? "border-cyan-400/60 text-cyan-300 bg-cyan-500/10" : "border-slate-700 text-slate-400 hover:border-slate-500")}
          >
            {s}
          </button>
        ))}
        <span className="w-px h-5 bg-slate-800 mx-1" />
        <button onClick={() => setScope(scope === "all" ? "function" : "all")} className="text-xs px-3 py-1 rounded-full border border-slate-700 text-slate-400 hover:border-slate-500">
          {scope === "all" ? "All functions" : `Only ${selectedFunction ?? "selected"}()`}
        </button>
        {factor && (
          <button onClick={() => onFactor(null)} className="text-xs px-3 py-1 rounded-full border border-cyan-400/60 text-cyan-300 bg-cyan-500/10">
            Factor: {labels[factor]} x
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5 mb-4">
        {factorsWithIssues.map((f) => (
          <FactorHint key={f.key} factor={f}>
          <button
            onClick={() => onFactor(factor === f.key ? null : f.key)}
            className={clsx("text-[11px] px-2 py-0.5 rounded border", factor === f.key ? "border-cyan-400/60 text-cyan-300" : "border-slate-800 text-slate-500 hover:text-slate-300")}
          >
            {f.label} {f.findings}
          </button>
          </FactorHint>
        ))}
      </div>

      <div className="text-xs text-slate-500 mb-2">{list.length} of {result.issues.length} findings</div>
      <div className="space-y-3 max-h-[760px] overflow-y-auto pr-1">
        {list.length === 0 && <Panel className="p-6 text-sm text-slate-500 text-center">Nothing matches these filters.</Panel>}
        {list.map((i) => (
          <Panel key={i.id} className={clsx("p-4", activeIssueId === i.id && "ring-1 ring-cyan-400/60")}>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <SeverityBadge severity={i.severity} />
              <span className="text-sm font-medium text-slate-100">{i.title}</span>
              <span className="text-[11px] text-slate-500 mono ml-auto">{i.id}</span>
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 mb-2">
              <span className="mono text-slate-300">{i.function}()</span>
              <span>lines {i.lines.length > 1 ? i.lines.slice(0, 8).join(", ") + (i.lines.length > 8 ? " ..." : "") : i.line_start}</span>
              <span>{i.metric_label}: <b className="text-slate-300">{i.metric_value}</b></span>
              <span className="text-slate-600">{labels[i.factor]}</span>
              {i.auto_fix && <span className="inline-flex items-center gap-1 text-emerald-400"><Wand2 size={11} /> auto-fixable</span>}
            </div>
            <div className="text-sm text-slate-300 mb-2"><span className="text-slate-500">Why: </span>{i.why}</div>
            <div className="text-sm text-slate-300 mb-3"><span className="text-slate-500">Fix: </span>{i.recommendation}</div>
            <pre className="mono text-[11px] text-slate-400 bg-slate-950/70 border border-slate-800 rounded-lg p-2.5 overflow-x-auto whitespace-pre">{i.evidence}</pre>
            <button onClick={() => onPick(i.id, i.function)} className="mt-3 inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300">
              <Crosshair size={12} /> Show in code
            </button>
          </Panel>
        ))}
      </div>
    </div>
  );
}
