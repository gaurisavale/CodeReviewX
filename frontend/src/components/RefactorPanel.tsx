"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { RefactorOut, RefactorSnapshot } from "@/lib/types";
import { Panel, scoreHex } from "./ui";
import { Wand2, Check, Copy, ArrowRight, Loader2, ShieldCheck } from "lucide-react";

const DiffEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.DiffEditor), { ssr: false });

function Delta({ label, a, b, lowerBetter }: { label: string; a: number; b: number; lowerBetter?: boolean }) {
  const better = lowerBetter ? b < a : b > a;
  const same = a === b;
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="flex items-center gap-2 mono text-sm">
        <span className="text-slate-400">{a}</span>
        <ArrowRight size={12} className="text-slate-600" />
        <span style={{ color: same ? "#94a3b8" : better ? "#10b981" : "#ef4444" }} className="font-semibold">{b}</span>
      </div>
    </div>
  );
}

function Scores({ before, after }: { before: RefactorSnapshot; after: RefactorSnapshot }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
      <Delta label="Health" a={before.overall_health} b={after.overall_health} />
      <Delta label="Max complexity" a={before.max_complexity} b={after.max_complexity} lowerBetter />
      <Delta label="Max nesting" a={before.max_nesting_depth} b={after.max_nesting_depth} lowerBetter />
      <Delta label="Longest function" a={before.max_function_length} b={after.max_function_length} lowerBetter />
      <Delta label="Findings" a={before.findings_total} b={after.findings_total} lowerBetter />
      <Delta label="Critical" a={before.critical} b={after.critical} lowerBetter />
    </div>
  );
}

export default function RefactorPanel({ refactor, onApply, applying, applied }: { refactor: RefactorOut | null; onApply: (code: string) => void; applying: boolean; applied: boolean }) {
  const [copied, setCopied] = useState(false);
  if (!refactor || !refactor.available || !refactor.refactored || !refactor.original || !refactor.before || !refactor.after) {
    return (
      <Panel className="p-6 text-sm text-slate-400">
        <div className="flex items-center gap-2 text-slate-200 font-medium mb-1"><ShieldCheck size={15} className="text-emerald-400" /> No automatic refactor</div>
        {refactor?.reason ?? "Nothing safe to change automatically."}
      </Panel>
    );
  }
  const code = refactor.refactored;
  return (
    <div className="space-y-4">
      <Panel className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <div className="text-sm font-medium text-slate-100">Suggested refactor</div>
            <div className="text-xs text-slate-500">
              Changes {refactor.functions?.length} function(s). Re-analyzed after generation: health{" "}
              <b style={{ color: scoreHex(refactor.before.overall_health) }}>{refactor.before.overall_health}</b> to{" "}
              <b style={{ color: scoreHex(refactor.after.overall_health) }}>{refactor.after.overall_health}</b>.
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(code);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                } catch {
                  /* clipboard unavailable */
                }
              }}
              className="inline-flex items-center gap-1.5 text-xs border border-slate-700 text-slate-300 rounded-lg px-3 py-2 hover:border-slate-500"
            >
              {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy code"}
            </button>
            <button
              disabled={applying || applied}
              onClick={() => onApply(code)}
              className="inline-flex items-center gap-1.5 text-sm font-medium rounded-lg px-4 py-2 bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 hover:brightness-110 disabled:opacity-60"
            >
              {applying ? <Loader2 size={14} className="animate-spin" /> : applied ? <Check size={14} /> : <Wand2 size={14} />}
              {applied ? "Applied and re-analyzed" : "Apply Suggested Refactor"}
            </button>
          </div>
        </div>
        <Scores before={refactor.before} after={refactor.after} />
      </Panel>

      <div className="grid lg:grid-cols-[340px_1fr] gap-4">
        <Panel className="p-5">
          <div className="text-xs uppercase tracking-wide text-slate-500 mb-3">What changed</div>
          <ol className="space-y-3">
            {refactor.steps?.map((s, i) => (
              <li key={i} className="text-sm">
                <div className="text-slate-200"><span className="text-slate-500 mr-1.5">{i + 1}.</span>{s.title}</div>
                <div className="text-xs text-slate-500 mt-0.5"><span className="mono text-slate-400">{s.function}()</span> - {s.detail}</div>
              </li>
            ))}
          </ol>
          {refactor.still_manual && refactor.still_manual.length > 0 && (
            <div className="mt-5 pt-4 border-t border-slate-800">
              <div className="text-xs uppercase tracking-wide text-amber-400 mb-2">Still needs a human</div>
              <ul className="text-xs text-slate-400 space-y-1 list-disc pl-4">
                {refactor.still_manual.map((m) => (<li key={m}>{m}</li>))}
              </ul>
            </div>
          )}
          <div className="mt-4 text-[11px] text-slate-600 leading-snug">{refactor.note}</div>
        </Panel>

        <Panel className="overflow-hidden">
          <div className="flex justify-between px-4 py-2.5 border-b border-slate-800 text-xs">
            <span className="text-red-300">BEFORE</span>
            <span className="text-emerald-300">AFTER (parses and compiles)</span>
          </div>
          <div className="h-[520px]">
            <DiffEditor
              height="100%"
              language="python"
              theme="vs-dark"
              original={refactor.original}
              modified={code}
              keepCurrentOriginalModel
              keepCurrentModifiedModel
              options={{ readOnly: true, renderSideBySide: true, minimap: { enabled: false }, fontSize: 12, scrollBeyondLastLine: false, originalEditable: false }}
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}
