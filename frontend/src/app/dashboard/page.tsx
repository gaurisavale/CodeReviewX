"use client";

import Link from "next/link";
import {
  HeartPulse,
  Wrench,
  AlertTriangle,
  Sigma,
  FileCode2,
  GitBranch,
  Plus,
} from "lucide-react";
import { useAnalysis } from "@/lib/store";
import MetricCard from "@/components/MetricCard";
import { Panel, RiskBadge } from "@/components/ui";

export default function DashboardPage() {
  const { current, history } = useAnalysis();

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-slate-50">AI Code Health Dashboard</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Understand your code. Understand why it needs improvement.
          </p>
        </div>
        <Link
          href="/dashboard/analyze"
          className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 font-medium rounded-xl px-4 py-2.5 hover:brightness-110 transition-all self-start"
        >
          <Plus size={16} /> New Analysis
        </Link>
      </div>

      {!current ? (
        <Panel className="p-10 text-center">
          <FileCode2 className="mx-auto text-slate-600 mb-4" size={32} />
          <div className="text-slate-200 font-medium mb-1">No analysis yet</div>
          <div className="text-slate-500 text-sm mb-5">
            Run your first analysis to see structural metrics, the function health
            graph, and XAI explanations here.
          </div>
          <Link
            href="/dashboard/analyze"
            className="inline-flex items-center gap-2 bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 rounded-lg px-4 py-2 text-sm hover:bg-cyan-500/20 transition-colors"
          >
            Start Analyzing <Plus size={14} />
          </Link>
        </Panel>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-slate-400">
              Showing results for <span className="text-slate-200 mono">{current.filename}</span>
            </div>
            <Link
              href="/dashboard/results"
              className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              Open full results →
            </Link>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <MetricCard
              icon={HeartPulse}
              label="Code Health"
              value={current.summary.overall_health}
              suffix={`/ 100 (${current.summary.grade})`}
              tooltip="Deterministic score: 60% line-weighted average function health plus 40% worst function. Any critical finding caps a function at 49."
              tone="emerald"
            />
            <MetricCard
              icon={Wrench}
              label="Maintainability"
              value={current.summary.maintainability_score}
              suffix="%"
              tooltip="Average of complexity, nesting, length, duplication, separation, naming and docs factor scores."
              tone="cyan"
            />
            <MetricCard
              icon={AlertTriangle}
              label="Findings"
              value={current.summary.findings_total}
              suffix={`(${current.summary.critical} critical)`}
              tooltip="Total findings from the rule engine, each with exact line evidence."
              tone="amber"
            />
            <MetricCard
              icon={Sigma}
              label="Functions"
              value={current.summary.functions}
              tooltip="Total number of functions detected by the AST analyzer."
              tone="purple"
            />
            <MetricCard
              icon={FileCode2}
              label="Lines of Code"
              value={current.summary.total_lines}
              tooltip="Total lines in the submitted file, including blanks and comments."
              tone="cyan"
            />
            <MetricCard
              icon={GitBranch}
              label="Max Complexity"
              value={current.summary.max_complexity}
              tooltip="Highest cyclomatic complexity among all functions."
              tone="red"
            />
          </div>

          {history.length > 1 && (
            <div className="mt-10">
              <div className="text-sm font-medium text-slate-300 mb-3">Recent Analyses</div>
              <Panel className="divide-y divide-slate-800/70">
                {history.slice(0, 5).map((h) => (
                  <div key={h.id} className="flex items-center justify-between px-5 py-3">
                    <div className="text-sm text-slate-200 mono">{h.filename}</div>
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>{h.functions} functions</span>
                      <span>{h.health}/10</span>
                      <RiskBadge risk={h.status} />
                    </div>
                  </div>
                ))}
              </Panel>
            </div>
          )}
        </>
      )}
    </div>
  );
}
