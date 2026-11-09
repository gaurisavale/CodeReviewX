"use client";

import { Panel } from "@/components/ui";
import { useAnalysis } from "@/lib/store";
import { Trash2 } from "lucide-react";

export default function SettingsPage() {
  const { clearHistory, history } = useAnalysis();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api";

  return (
    <div className="p-6 sm:p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-50 mb-6">Settings</h1>

      <Panel className="p-5 mb-5">
        <div className="text-sm font-medium text-slate-200 mb-2">Backend</div>
        <p className="text-xs text-slate-500 mb-2">
          CodeReviewX connects to the FastAPI backend at:
        </p>
        <code className="text-xs text-cyan-300 bg-slate-900/70 border border-slate-800 rounded-lg px-3 py-1.5 block mono">
          {apiUrl}
        </code>
        <p className="text-xs text-slate-600 mt-2">
          Set <code className="mono">NEXT_PUBLIC_API_URL</code> in <code className="mono">.env.local</code> to change it.
        </p>
      </Panel>

      <Panel className="p-5">
        <div className="text-sm font-medium text-slate-200 mb-2">Local Data</div>
        <p className="text-xs text-slate-500 mb-4">
          {history.length} analysis{history.length === 1 ? "" : "es"} stored in this browser.
        </p>
        <button
          onClick={clearHistory}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-red-400 border border-slate-700 hover:border-red-500/40 rounded-lg px-3 py-1.5 transition-colors"
        >
          <Trash2 size={13} /> Clear all local history
        </button>
      </Panel>
    </div>
  );
}
