"use client";

import { useState } from "react";
import { createPortal } from "react-dom";
import { FactorMeta } from "@/lib/types";
import { scoreHex } from "./ui";

interface Pos {
  x: number;
  y: number;
}

/** Hover card explaining a factor: what it is, what is measured, how the score is computed. */
export default function FactorHint({
  factor,
  scope,
  score,
  findings,
  children,
  className,
}: {
  factor: FactorMeta;
  scope?: string;
  score?: number;
  findings?: number;
  children: React.ReactNode;
  className?: string;
}) {
  const [pos, setPos] = useState<Pos | null>(null);
  const shown = score ?? factor.score;
  const count = findings ?? factor.findings;

  function show(e: React.MouseEvent<HTMLSpanElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    const w = 340;
    const x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    const below = r.bottom + 8;
    const y = below + 260 > window.innerHeight ? Math.max(8, r.top - 268) : below;
    setPos({ x, y });
  }

  return (
    <span className={className} onMouseEnter={show} onMouseLeave={() => setPos(null)}>
      {children}
      {pos &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            style={{ position: "fixed", left: pos.x, top: pos.y, width: 340, zIndex: 1000 }}
            className="pointer-events-none rounded-xl border border-slate-700 bg-[#0b0f18] shadow-2xl p-4 text-left normal-case tracking-normal"
          >
            <div className="flex items-baseline justify-between mb-2">
              <div className="text-sm font-semibold text-slate-100">{factor.label}</div>
              <div className="text-xs text-slate-500">
                {scope ? `${scope}: ` : "file: "}
                <b style={{ color: scoreHex(shown) }}>{shown}/100</b>
                {count > 0 ? `, ${count} finding${count > 1 ? "s" : ""}` : ""}
              </div>
            </div>
            <div className="text-[11px] uppercase tracking-wide text-cyan-400 mb-0.5">What it is</div>
            <p className="text-xs text-slate-300 leading-snug mb-2">{factor.what}</p>
            <div className="text-[11px] uppercase tracking-wide text-purple-400 mb-0.5">What is measured</div>
            <p className="text-xs text-slate-300 leading-snug mb-2">{factor.measures}</p>
            <div className="text-[11px] uppercase tracking-wide text-emerald-400 mb-0.5">How it is scored</div>
            <p className="text-xs text-slate-300 leading-snug mb-2">{factor.how}</p>
            <div className="text-[10px] text-slate-500 border-t border-slate-800 pt-2">
              Weight {factor.weight} in the function health score (weighted average of all 13 factors). Any critical finding caps a function at 49.
            </div>
          </div>,
          document.body
        )}
    </span>
  );
}
