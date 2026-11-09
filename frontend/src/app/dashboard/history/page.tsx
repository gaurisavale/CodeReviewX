"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2, FileClock, GitBranch, FileCode2 } from "lucide-react";
import { useAnalysis } from "@/lib/store";
import { deleteRun, listHistory, openRun } from "@/lib/api";
import { AnalyzeResponse, RunRow } from "@/lib/types";
import { Panel, scoreHex } from "@/components/ui";

export default function HistoryPage() {
  const { setCurrent } = useAnalysis();
  const router = useRouter();
  const [rows, setRows] = useState<RunRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    listHistory().then(setRows).catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function open(r: RunRow) {
    try {
      if (r.kind === "file") {
        const full = await openRun<AnalyzeResponse & { code: string }>(r.id);
        setCurrent(full, full.code);
        router.push("/dashboard/results");
      } else {
        router.push(`/dashboard/repo?run=${r.id}`);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="p-6 sm:p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-50">Analysis History</h1>
        <p className="text-slate-500 mt-1 text-sm">Every run is stored in the backend database, so history follows the project and survives browser resets.</p>
      </div>
      {error && <div className="mb-4 text-sm text-red-400">{error}</div>}
      {rows && rows.length === 0 ? (
        <Panel className="p-10 text-center">
          <FileClock className="mx-auto text-slate-600 mb-4" size={32} />
          <div className="text-slate-200 font-medium mb-1">No analyses yet</div>
          <div className="text-slate-500 text-sm">Run an analysis or scan a repository to see it here.</div>
        </Panel>
      ) : (
        <Panel className="divide-y divide-slate-800/70">
          {(rows ?? []).map((r) => (
            <div key={r.id} className="flex items-center justify-between px-5 py-4 hover:bg-slate-800/30 transition-colors">
              <button onClick={() => open(r)} className="flex items-center gap-3 text-left flex-1 min-w-0">
                {r.kind === "file" ? <FileCode2 size={16} className="text-slate-500" /> : <GitBranch size={16} className="text-cyan-400" />}
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-100 mono truncate">{r.label}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{new Date(r.created_at).toLocaleString()} · {r.kind === "file" ? "single file" : `${r.files} files`}</div>
                </div>
              </button>
              <div className="flex items-center gap-5 text-xs text-slate-400 shrink-0">
                <span style={{ color: scoreHex(r.overall_health) }} className="font-semibold text-sm">{r.overall_health} ({r.grade})</span>
                <span>{r.functions} functions</span>
                <span>{r.findings} findings</span>
                <span className="text-amber-400">{r.high_risk_functions} high bug-risk</span>
                <button onClick={() => deleteRun(r.id).then(load)} className="text-slate-600 hover:text-red-400" aria-label="Delete run"><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </Panel>
      )}
    </div>
  );
}
