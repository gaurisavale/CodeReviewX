"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { FolderKanban, Plus, Trash2 } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import { createProject, deleteProject, listProjects } from "@/lib/api";
import { ProjectRow } from "@/lib/types";
import { Panel, scoreHex } from "@/components/ui";

export default function ProjectsPage() {
  const [rows, setRows] = useState<ProjectRow[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    listProjects().then(setRows).catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  async function add() {
    if (!name.trim()) return;
    setError(null);
    try {
      await createProject(name.trim());
      setName("");
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="p-6 sm:p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-50 mb-1">Projects</h1>
      <p className="text-slate-500 text-sm mb-6">Group repository scans under a project to track code health over time.</p>

      <div className="flex gap-2 mb-6">
        <input value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} placeholder="New project name"
          className="flex-1 rounded-lg bg-slate-900/60 border border-slate-700 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500/50" />
        <button onClick={add} className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 px-4 text-sm hover:bg-cyan-500/25"><Plus size={14} /> Create</button>
      </div>
      {error && <div className="mb-4 text-sm text-red-400">{error}</div>}

      {rows && rows.length === 0 ? (
        <Panel className="p-10 text-center">
          <FolderKanban className="mx-auto text-slate-600 mb-4" size={32} />
          <div className="text-slate-200 font-medium mb-1">No projects yet</div>
          <div className="text-slate-500 text-sm">Create one, then pick it on the Repo Scan page.</div>
        </Panel>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {(rows ?? []).map((p) => (
            <Panel key={p.id} className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-slate-100 font-medium">{p.name}</div>
                  <div className="text-xs text-slate-500">{p.runs} run{p.runs === 1 ? "" : "s"}</div>
                </div>
                <div className="flex items-center gap-3">
                  {p.latest_health !== null && <span className="text-2xl font-semibold" style={{ color: scoreHex(p.latest_health) }}>{p.latest_health}<span className="text-xs text-slate-500 ml-1">{p.latest_grade}</span></span>}
                  <button onClick={() => deleteProject(p.id).then(load)} className="text-slate-600 hover:text-red-400" aria-label="Delete project"><Trash2 size={14} /></button>
                </div>
              </div>
              {p.trend.length > 1 && (
                <div className="h-20 mt-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={p.trend}>
                      <YAxis hide domain={[0, 100]} />
                      <Tooltip contentStyle={{ background: "#0b1020", border: "1px solid #1e293b", fontSize: 11 }} formatter={(v) => [`${v}`, "health"]} labelFormatter={() => ""} />
                      <Area type="monotone" dataKey="health" stroke="#22d3ee" fill="#22d3ee33" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
              <Link href={`/dashboard/repo?project=${p.id}`} className="inline-block mt-3 text-xs text-cyan-400 hover:text-cyan-300">Scan into this project →</Link>
            </Panel>
          ))}
        </div>
      )}
    </div>
  );
}
