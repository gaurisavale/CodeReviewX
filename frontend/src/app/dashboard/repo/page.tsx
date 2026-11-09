"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { GitBranch, Loader2, Upload } from "lucide-react";
import { analyzeGithub, analyzeZip, listProjects, openRun } from "@/lib/api";
import { AnalyzeResponse, ProjectRow, RepoReport } from "@/lib/types";
import { useAnalysis } from "@/lib/store";
import { Panel, ProgressBar, scoreColorClass, scoreHex } from "@/components/ui";

function RepoScan() {
  const params = useSearchParams();
  const router = useRouter();
  const { setCurrent } = useAnalysis();
  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [projectId, setProjectId] = useState<number | undefined>(params.get("project") ? Number(params.get("project")) : undefined);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<RepoReport | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listProjects().then(setProjects).catch(() => {});
    const run = params.get("run");
    if (run) openRun<RepoReport & { project: RepoReport["project"]; file_runs?: { id: number; label: string; overall_health: number; grade: string; functions: number; findings: number; critical: number; high_risk_functions: number; max_defect_risk: number }[] }>(Number(run))
      .then((r) => setReport({ ...r, files: (r.file_runs ?? []).map((f) => ({ id: f.id, filename: f.label, health: f.overall_health, grade: f.grade, functions: f.functions, findings: f.findings, critical: f.critical, high_risk: f.high_risk_functions, max_risk: f.max_defect_risk })) }))
      .catch((e) => setError(e.message));
  }, [params]);

  async function run(fn: () => Promise<RepoReport>) {
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      setReport(await fn());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function openFile(id: number) {
    const full = await openRun<AnalyzeResponse & { code: string }>(id);
    setCurrent(full, full.code);
    router.push("/dashboard/results");
  }

  const p = report?.project;
  return (
    <div className="p-6 sm:p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-50 mb-1">Repository scan</h1>
      <p className="text-slate-500 text-sm mb-6">Analyse a whole codebase: upload a ZIP or paste a public GitHub URL. Every .py file is scored, ranked by defect risk and stored.</p>

      <Panel className="p-5 mb-6">
        <div className="grid md:grid-cols-[1fr_auto] gap-3 items-end">
          <div className="flex gap-2">
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/pallets/click"
              className="flex-1 rounded-lg bg-slate-900/60 border border-slate-700 px-3 py-2 text-sm text-slate-100 mono outline-none focus:border-cyan-500/50" />
            <button disabled={busy || !url.trim()} onClick={() => run(() => analyzeGithub(url.trim(), projectId))}
              className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 px-4 text-sm hover:bg-cyan-500/25 disabled:opacity-40"><GitBranch size={14} /> Scan GitHub</button>
            <input ref={fileRef} type="file" accept=".zip" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) run(() => analyzeZip(f, projectId)); e.target.value = ""; }} />
            <button disabled={busy} onClick={() => fileRef.current?.click()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 text-slate-300 px-4 text-sm hover:bg-slate-800/50 disabled:opacity-40"><Upload size={14} /> Upload ZIP</button>
          </div>
          <select value={projectId ?? ""} onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : undefined)}
            className="rounded-lg bg-slate-900/60 border border-slate-700 px-3 py-2 text-sm text-slate-300">
            <option value="">No project</option>
            {projects.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
        </div>
        {busy && <div className="mt-3 text-sm text-slate-400 flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Scanning files...</div>}
        {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
      </Panel>

      {p && report && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[["Health", `${p.overall_health} (${p.grade})`, scoreHex(p.overall_health)], ["Files", p.files, ""], ["Functions", p.functions, ""], ["Findings", `${p.findings} (${p.critical} critical)`, ""], ["High bug-risk", p.high_risk_functions, "#f59e0b"]].map(([k, v, c]) => (
              <Panel key={String(k)} className="p-4"><div className="text-[11px] uppercase text-slate-500">{k}</div><div className="text-xl font-semibold text-slate-50" style={c ? { color: String(c) } : undefined}>{v}</div></Panel>
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <Panel className="p-5">
              <div className="text-sm font-semibold text-slate-100 mb-3">Riskiest functions (trained model)</div>
              <div className="space-y-2">
                {p.riskiest_functions.map((f) => (
                  <div key={`${f.file}:${f.name}`} className="flex items-center justify-between text-xs">
                    <div className="min-w-0"><span className="mono text-slate-200">{f.name}()</span> <span className="text-slate-500 truncate">{f.file}:{f.line}</span></div>
                    <div className="flex items-center gap-3 shrink-0"><span className="text-slate-400">health {f.health}</span><span className="text-amber-400 w-12 text-right">{(f.risk * 100).toFixed(1)}%</span></div>
                  </div>
                ))}
              </div>
            </Panel>
            <Panel className="p-5">
              <div className="text-sm font-semibold text-slate-100 mb-3">Factor scores across the codebase</div>
              <div className="space-y-1.5">
                {Object.entries(p.factor_scores).sort((a, b) => a[1] - b[1]).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2 text-[11px]"><span className="w-28 text-slate-400">{k.replace("_", " ")}</span><div className="flex-1"><ProgressBar value={v} colorClass={scoreColorClass(v)} /></div><span className="w-7 text-right text-slate-300">{v}</span></div>
                ))}
              </div>
            </Panel>
          </div>

          <Panel className="p-5">
            <div className="text-sm font-semibold text-slate-100 mb-3">Files, worst first (click to open the full analysis)</div>
            <div className="divide-y divide-slate-800/70 text-xs">
              {report.files.map((f) => (
                <button key={f.id} onClick={() => openFile(f.id)} className="w-full flex items-center justify-between py-2 text-left hover:bg-slate-800/30 px-2 rounded">
                  <span className="mono text-slate-200 truncate">{f.filename}</span>
                  <span className="flex items-center gap-4 shrink-0 text-slate-400"><span>{f.functions} fn</span><span>{f.findings} findings</span><span className="text-amber-400">{f.high_risk} high risk</span><span className="font-semibold w-12 text-right" style={{ color: scoreHex(f.health) }}>{f.health} {f.grade}</span></span>
                </button>
              ))}
            </div>
            {report.errors.length > 0 && <div className="mt-3 text-xs text-slate-500">{report.errors.length} file(s) could not be parsed, e.g. {report.errors[0].file}: {report.errors[0].message}</div>}
            {report.notes.map((n) => <div key={n} className="mt-1 text-xs text-slate-600">{n}</div>)}
          </Panel>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return <Suspense fallback={null}><RepoScan /></Suspense>;
}
