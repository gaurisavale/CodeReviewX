"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAnalysis } from "@/lib/store";
import { analyzeCode, ApiError } from "@/lib/api";
import FunctionHealthGraph from "@/components/FunctionHealthGraph";
import XaiSidebar from "@/components/XaiSidebar";
import CodeHealthBreakdown from "@/components/CodeHealthBreakdown";
import FindingsPanel from "@/components/FindingsPanel";
import FactorHeatmap from "@/components/FactorHeatmap";
import OverviewPanel from "@/components/OverviewPanel";
import CodeViewer from "@/components/CodeViewer";
import RefactorPanel from "@/components/RefactorPanel";
import { Panel } from "@/components/ui";
import { FileCode2, Plus } from "lucide-react";

function Heading({ n, title, sub }: { n: string; title: string; sub: string }) {
  return (
    <div className="mb-3 mt-10">
      <div className="text-[11px] uppercase tracking-widest text-cyan-400/80">{n}</div>
      <h2 className="text-lg font-semibold text-slate-50">{title}</h2>
      <p className="text-xs text-slate-500">{sub}</p>
    </div>
  );
}

export default function ResultsPage() {
  const { current, currentCode, selectedFunction, setSelectedFunction, setCurrent } = useAnalysis();
  const router = useRouter();
  const [factor, setFactor] = useState<string | null>(null);
  const [activeIssueId, setActiveIssueId] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!current) {
    return (
      <div className="p-6 sm:p-8 max-w-3xl mx-auto">
        <Panel className="p-10 text-center">
          <FileCode2 className="mx-auto text-slate-600 mb-4" size={32} />
          <div className="text-slate-200 font-medium mb-1">No analysis to show</div>
          <div className="text-slate-500 text-sm mb-5">Run an analysis first.</div>
          <Link href="/dashboard/analyze" className="inline-flex items-center gap-2 bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 rounded-lg px-4 py-2 text-sm hover:bg-cyan-500/20 transition-colors">
            New Analysis <Plus size={14} />
          </Link>
        </Panel>
      </div>
    );
  }

  const activeIssue = current.issues.find((i) => i.id === activeIssueId) ?? null;

  function pickFunction(fn: string, f: string | null) {
    setSelectedFunction(fn);
    setFactor(f);
    setActiveIssueId(null);
  }

  async function applyRefactor(code: string) {
    if (!current) return;
    setApplying(true);
    setError(null);
    try {
      const result = await analyzeCode(code, current.filename);
      setCurrent(result, code);
      setApplied(true);
      setActiveIssueId(null);
      setFactor(null);
      window.scrollTo({ top: 0, behavior: "smooth" });
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not re-analyze the refactored code.");
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-50">Analysis Report</h1>
          <p className="text-slate-500 mt-1 text-sm mono">{current.filename}</p>
        </div>
        <Link href="/dashboard/analyze" className="inline-flex items-center gap-2 border border-slate-700 text-slate-200 rounded-xl px-4 py-2 text-sm hover:border-slate-500 hover:bg-slate-800/40 transition-colors">
          <Plus size={14} /> New Analysis
        </Link>
      </div>
      {applied && !error && <div className="mb-4 text-sm text-emerald-300 border border-emerald-500/30 bg-emerald-500/10 rounded-lg px-4 py-2">Refactor applied. This report is now the analysis of the refactored code (see History for the original).</div>}
      {error && <div className="mb-4 text-sm text-red-300 border border-red-500/30 bg-red-500/10 rounded-lg px-4 py-2">{error}</div>}

      <OverviewPanel result={current} onPickIssue={(id) => { const i = current.issues.find((x) => x.id === id); if (i) { setSelectedFunction(i.function); setActiveIssueId(id); } }} />

      <Heading n="01 MEASURE" title="Factor Heat Map" sub="Every function against all 13 factors. Red is where to look first." />
      <Panel className="p-4">
        <FactorHeatmap result={current} selected={selectedFunction} activeFactor={factor} onSelect={pickFunction} />
      </Panel>

      <Heading n="02 EXPLAIN + VISUALIZE" title="Function Health Graph" sub="Callers on top, callees below. Strip under each name = the 13 factor scores. Click a node." />
      <div className="grid lg:grid-cols-[1fr_380px] gap-5">
        <Panel className="h-[560px] overflow-hidden">
          <FunctionHealthGraph result={current} selected={selectedFunction} onSelect={(n) => pickFunction(n, null)} />
        </Panel>
        <XaiSidebar result={current} selectedFunction={selectedFunction} />
      </div>
      <div className="flex items-center gap-5 mt-3 text-xs text-slate-400">
        <Legend color="#10b981" label="Healthy (75+)" />
        <Legend color="#f59e0b" label="Warning (50-74)" />
        <Legend color="#ef4444" label="Critical (below 50)" />
      </div>

      <Heading n="03 FINDINGS" title="Every issue, with evidence" sub="Filter by severity, factor or function. Each finding has exact lines, why it matters, and a fix." />
      <div className="grid lg:grid-cols-[360px_1fr] gap-5">
        <CodeHealthBreakdown factors={current.factors} categories={current.categories} />
        <FindingsPanel
          result={current}
          selectedFunction={selectedFunction}
          factor={factor}
          activeIssueId={activeIssueId}
          onFactor={setFactor}
          onPick={(id, fn) => { setActiveIssueId(id); setSelectedFunction(fn); document.getElementById("code-view")?.scrollIntoView({ behavior: "smooth", block: "center" }); }}
        />
      </div>

      <div id="code-view">
        <Heading n="04 CODE" title="Code reference" sub="Selected function is tinted. A chosen finding highlights its exact lines." />
        <CodeViewer code={currentCode} result={current} selectedFunction={selectedFunction} issue={activeIssue} />
      </div>

      <Heading n="05 REFACTOR" title="Refactoring" sub="Generated by AST transformations, re-parsed and re-scored. Apply to re-run the whole analysis on the new code." />
      <RefactorPanel refactor={current.refactor} onApply={applyRefactor} applying={applying} applied={false} />
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
      {label}
    </div>
  );
}
