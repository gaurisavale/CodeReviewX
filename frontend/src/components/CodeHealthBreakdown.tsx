"use client";

import { FactorMeta } from "@/lib/types";
import FactorHint from "./FactorHint";
import { Panel, ProgressBar, scoreColorClass, scoreTextColor } from "./ui";

export default function CodeHealthBreakdown({ factors, categories }: { factors: FactorMeta[]; categories: Record<string, number> }) {
  return (
    <Panel className="p-5">
      <div className="text-sm font-medium text-slate-200 mb-4">Code Health Breakdown</div>
      <div className="grid grid-cols-5 gap-2 mb-5">
        {Object.entries(categories).map(([k, v]) => (
          <div key={k} className="text-center rounded-lg border border-slate-800 bg-slate-900/40 py-2">
            <div className={`text-lg font-semibold ${scoreTextColor(v)}`}>{v}</div>
            <div className="text-[9px] text-slate-500 capitalize truncate px-0.5">{k}</div>
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {factors.map((f) => (
          <FactorHint key={f.key} factor={f} className="block cursor-help">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">{f.label} <span className="text-slate-600">w{f.weight}</span></span>
              <span className={scoreTextColor(f.score)}>{f.score}{f.findings ? ` (${f.findings})` : ""}</span>
            </div>
            <ProgressBar value={f.score} colorClass={scoreColorClass(f.score)} />
          </FactorHint>
        ))}
      </div>
    </Panel>
  );
}
