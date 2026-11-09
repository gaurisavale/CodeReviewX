"use client";

import { AnalyzeResponse } from "@/lib/types";
import FactorHint from "./FactorHint";
import { Panel, ProgressBar, RiskBadge, scoreColorClass, scoreHex } from "./ui";
import { Brain, Ruler, Lightbulb, Layers, ArrowRightLeft, Activity } from "lucide-react";

function Section({ icon: Icon, title, tone, children }: { icon: typeof Brain; title: string; tone: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <div className={`flex items-center gap-2 text-xs font-semibold uppercase tracking-wide mb-2 ${tone}`}>
        <Icon size={13} /> {title}
      </div>
      {children}
    </div>
  );
}

export default function XaiSidebar({ result, selectedFunction }: { result: AnalyzeResponse; selectedFunction: string | null }) {
  const fn = result.functions.find((f) => f.name === selectedFunction) ?? result.functions[0];
  if (!fn) return <Panel className="p-5 text-sm text-slate-500">No functions found.</Panel>;
  const meta = Object.fromEntries(result.factors.map((f) => [f.key, f]));
  const factorRows = Object.entries(fn.factors).sort((a, b) => a[1].score - b[1].score);
  const metrics: [string, string | number][] = [
    ["Cyclomatic", fn.complexity],
    ["Cognitive", fn.cognitive],
    ["Nesting", fn.nesting_depth],
    ["Lines", fn.lines],
    ["Parameters", fn.parameters],
    ["elif chain", fn.elif_chain || "-"],
  ];
  return (
    <Panel className="p-5 h-[560px] overflow-y-auto">
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Explainable AI</div>
          <div className="mono text-slate-50 text-lg truncate">{fn.name}()</div>
          <div className="text-xs text-slate-500">lines {fn.line_start}-{fn.line_end}</div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-3xl font-semibold" style={{ color: scoreHex(fn.health_score) }}>{fn.health_score}</div>
          <RiskBadge risk={fn.risk} />
        </div>
      </div>
      <p className="text-xs text-slate-400 mt-2 mb-5">{fn.purpose}</p>

      <Section icon={Brain} title="Why this score" tone="text-purple-400">
        <p className="text-sm text-slate-300 leading-relaxed">{fn.explanation.why}</p>
      </Section>

      {fn.defect_risk && (
        <Section icon={Activity} title="Bug-fix likelihood (trained model)" tone="text-amber-400">
          <div className="flex items-center gap-3 mb-2">
            <div className="text-2xl font-semibold text-slate-50">{(fn.defect_risk.probability * 100).toFixed(1)}%</div>
            <RiskBadge risk={fn.defect_risk.band} />
            <span className="text-[11px] text-slate-500">of similar functions needed a later bug fix</span>
          </div>
          <ul className="space-y-1">
            {fn.defect_risk.drivers.map((d) => (
              <li key={d.name} className="flex items-center justify-between text-xs text-slate-400">
                <span>{d.name}</span>
                <span className={d.direction === "raises" ? "text-red-400" : "text-emerald-400"}>
                  {d.direction === "raises" ? "raises" : "lowers"} risk ({d.effect > 0 ? "+" : ""}{d.effect.toFixed(2)})
                </span>
              </li>
            ))}
          </ul>
          <div className="text-[10px] text-slate-600 mt-2">Logistic regression, {result.ml ? `AUC ${result.ml.auc} on held-out repos` : "trained on open-source history"}. Ranks risk; it does not change the health score.</div>
        </Section>
      )}

      <Section icon={Ruler} title="Structural evidence" tone="text-cyan-400">
        <div className="grid grid-cols-3 gap-2 mb-3">
          {metrics.map(([k, v]) => (
            <div key={k} className="rounded-lg border border-slate-800 bg-slate-900/40 px-2 py-1.5 text-center">
              <div className="text-[10px] text-slate-500">{k}</div>
              <div className="mono text-slate-100 text-sm">{v}</div>
            </div>
          ))}
        </div>
        <div className="space-y-1.5 mb-3">
          {factorRows.map(([k, c]) => (
            <FactorHint key={k} factor={meta[k]} scope={`${fn.name}()`} score={c.score} findings={c.findings} className="block cursor-help">
              <div className="flex items-center gap-2 text-[11px]">
                <span className="w-24 text-slate-400 shrink-0 underline decoration-dotted decoration-slate-600">{meta[k].label}</span>
                <div className="flex-1"><ProgressBar value={c.score} colorClass={scoreColorClass(c.score)} /></div>
                <span className="w-7 text-right text-slate-300">{c.score}</span>
              </div>
            </FactorHint>
          ))}
        </div>
        <ul className="space-y-1.5">
          {fn.explanation.evidence.map((e, i) => (
            <li key={i} className="text-xs text-slate-400 leading-snug border-l-2 border-slate-700 pl-2">{e}</li>
          ))}
        </ul>
      </Section>

      {fn.responsibilities.length > 0 && (
        <Section icon={Layers} title="Responsibilities detected" tone="text-amber-400">
          <div className="flex flex-wrap gap-1.5">
            {fn.responsibilities.map((r) => (
              <span key={r.name} title={`lines ${r.lines.join(", ")}`} className="text-xs px-2 py-1 rounded-full border border-slate-700 text-slate-300">
                {r.name}
              </span>
            ))}
          </div>
        </Section>
      )}

      {(fn.calls.length > 0 || fn.called_by.length > 0) && (
        <Section icon={ArrowRightLeft} title="Call relationships" tone="text-slate-400">
          <div className="text-xs text-slate-400 space-y-1">
            <div className="flex flex-wrap gap-x-2">Calls: {fn.calls.length ? fn.calls.map((c) => <span key={c} className="mono text-slate-200">{c}()</span>) : "none"}</div>
            <div className="flex flex-wrap gap-x-2">Called by: {fn.called_by.length ? fn.called_by.map((c) => <span key={c} className="mono text-slate-200">{c}()</span>) : "nobody in this file"}</div>
          </div>
        </Section>
      )}

      <Section icon={Lightbulb} title="Recommendation" tone="text-emerald-400">
        <p className="text-sm text-slate-300 leading-relaxed">{fn.explanation.recommendation}</p>
      </Section>
    </Panel>
  );
}
