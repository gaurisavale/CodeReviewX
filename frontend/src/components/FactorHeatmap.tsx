"use client";

import clsx from "clsx";
import { AnalyzeResponse } from "@/lib/types";
import { scoreHex } from "./ui";
import FactorHint from "./FactorHint";

function cellBg(score: number): string {
  const hex = scoreHex(score);
  const alpha = score >= 90 ? "22" : score >= 75 ? "44" : score >= 50 ? "66" : "88";
  return `${hex}${alpha}`;
}

export default function FactorHeatmap({
  result,
  selected,
  activeFactor,
  onSelect,
}: {
  result: AnalyzeResponse;
  selected: string | null;
  activeFactor: string | null;
  onSelect: (fn: string, factor: string | null) => void;
}) {
  const factors = result.factors;
  const fns = result.functions;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1 text-xs min-w-[920px]">
        <thead>
          <tr>
            <th className="text-left text-slate-500 font-medium px-2 pb-1 sticky left-0 bg-[#0a0d16] z-10 w-60">Function</th>
            <th className="text-slate-400 font-medium pb-1">Health</th>
            {factors.map((f) => (
              <th key={f.key} className={clsx("font-medium pb-1 px-0.5 align-bottom cursor-help", activeFactor === f.key ? "text-cyan-300" : "text-slate-500")}>
                <FactorHint factor={f} className="block">
                  <div className="[writing-mode:vertical-rl] rotate-180 mx-auto h-20 text-[11px] whitespace-nowrap">{f.label}</div>
                </FactorHint>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {fns.map((fn) => (
            <tr key={fn.name} className={clsx(selected === fn.name && "outline outline-1 outline-cyan-400/50")}>
              <td
                onClick={() => onSelect(fn.name, null)}
                className="px-2 py-1 mono text-slate-200 cursor-pointer whitespace-nowrap sticky left-0 bg-[#0a0d16] z-10 hover:text-cyan-300"
              >
                {fn.name}()
                <span className="text-slate-600 ml-2">L{fn.line_start}</span>
              </td>
              <td className="text-center">
                <span
                  className="inline-block rounded-md px-2 py-1 font-semibold min-w-[40px]"
                  style={{ background: cellBg(fn.health_score), color: scoreHex(fn.health_score) }}
                >
                  {fn.health_score}
                </span>
              </td>
              {factors.map((f) => {
                const c = fn.factors[f.key];
                return (
                  <td key={f.key} className="text-center">
                    <FactorHint factor={f} scope={`${fn.name}()`} score={c.score} findings={c.findings} className="block">
                    <button
                      onClick={() => onSelect(fn.name, f.key)}
                      className={clsx(
                        "w-full rounded-md py-1.5 font-medium transition-transform hover:scale-110 relative",
                        selected === fn.name && activeFactor === f.key && "ring-2 ring-cyan-300"
                      )}
                      style={{ background: cellBg(c.score), color: c.score >= 90 ? "#64748b" : scoreHex(c.score) }}
                    >
                      {c.score}
                      {c.findings > 0 && (
                        <span className="absolute -top-1 -right-1 text-[9px] rounded-full bg-slate-900 border border-slate-600 text-slate-300 w-4 h-4 leading-[14px]">
                          {c.findings}
                        </span>
                      )}
                    </button>
                    </FactorHint>
                  </td>
                );
              })}
            </tr>
          ))}
          <tr>
            <td className="px-2 pt-2 text-slate-400 sticky left-0 bg-[#0a0d16] z-10">File average</td>
            <td className="pt-2 text-center">
              <span className="inline-block rounded-md px-2 py-1 font-semibold" style={{ background: cellBg(result.summary.overall_health), color: scoreHex(result.summary.overall_health) }}>
                {result.summary.overall_health}
              </span>
            </td>
            {factors.map((f) => (
              <td key={f.key} className="pt-2 text-center">
                <span className="inline-block w-full rounded-md py-1.5 font-semibold" style={{ background: cellBg(f.score), color: scoreHex(f.score) }}>
                  {f.score}
                </span>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      <div className="flex flex-wrap items-center gap-4 mt-3 text-[11px] text-slate-500">
        <span className="flex items-center gap-1.5"><i className="w-3 h-3 rounded" style={{ background: "#10b98166" }} /> 75-100 healthy</span>
        <span className="flex items-center gap-1.5"><i className="w-3 h-3 rounded" style={{ background: "#f59e0b88" }} /> 50-74 needs work</span>
        <span className="flex items-center gap-1.5"><i className="w-3 h-3 rounded" style={{ background: "#ef444488" }} /> 0-49 critical</span>
        <span>Small badge = number of findings. Click a cell to filter the findings below.</span>
      </div>
    </div>
  );
}
