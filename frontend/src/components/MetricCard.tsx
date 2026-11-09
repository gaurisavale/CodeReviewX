"use client";

import { useState } from "react";
import { LucideIcon, Info } from "lucide-react";
import clsx from "clsx";

export default function MetricCard({
  icon: Icon,
  label,
  value,
  suffix,
  tooltip,
  tone = "cyan",
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  suffix?: string;
  tooltip: string;
  tone?: "cyan" | "emerald" | "amber" | "red" | "purple";
}) {
  const [showTip, setShowTip] = useState(false);

  const toneMap: Record<string, string> = {
    cyan: "text-cyan-400 bg-cyan-500/10",
    emerald: "text-emerald-400 bg-emerald-500/10",
    amber: "text-amber-400 bg-amber-500/10",
    red: "text-red-400 bg-red-500/10",
    purple: "text-purple-400 bg-purple-500/10",
  };

  return (
    <div className="glass-panel rounded-2xl p-5 relative fade-in-up">
      <div className="flex items-start justify-between">
        <div className={clsx("w-9 h-9 rounded-lg flex items-center justify-center", toneMap[tone])}>
          <Icon size={17} />
        </div>
        <button
          onMouseEnter={() => setShowTip(true)}
          onMouseLeave={() => setShowTip(false)}
          className="text-slate-600 hover:text-slate-400"
        >
          <Info size={14} />
        </button>
      </div>
      <div className="mt-4 text-2xl font-semibold text-slate-50">
        {value}
        {suffix && <span className="text-sm text-slate-500 ml-1">{suffix}</span>}
      </div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
      {showTip && (
        <div className="absolute z-10 top-3 right-3 translate-x-1 w-48 text-[11px] leading-snug text-slate-300 bg-slate-900 border border-slate-700 rounded-lg p-2.5 shadow-xl">
          {tooltip}
        </div>
      )}
    </div>
  );
}
