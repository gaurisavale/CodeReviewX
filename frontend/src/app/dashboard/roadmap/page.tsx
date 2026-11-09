import { Panel } from "@/components/ui";
import { CheckCircle2, Circle } from "lucide-react";

const CURRENT = [
  "Single-file analysis",
  "Python-first structural support (real AST analysis)",
  "Deterministic scoring — no random or invented metrics",
  "Fallback AI explanations with no API key required",
];

const FUTURE = [
  "Repository-wide analysis",
  "Multi-file dependency analysis",
  "AST support for more languages (JS/TS, Java, C++)",
  "Code duplication detection",
  "Security vulnerability analysis",
  "GitHub integration",
  "GitLab integration",
  "CI/CD integration",
  "Technical debt estimation",
  "SHAP/LIME explainability",
  "Team dashboards",
  "Local / self-hosted AI models",
];

export default function RoadmapPage() {
  return (
    <div className="p-6 sm:p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-50 mb-1">Limitations &amp; Roadmap</h1>
      <p className="text-slate-500 text-sm mb-8">
        What CodeReviewX does today, and where it&apos;s headed next.
      </p>

      <div className="grid sm:grid-cols-2 gap-5">
        <Panel className="p-5">
          <div className="text-sm font-medium text-emerald-300 mb-4">Current MVP</div>
          <ul className="space-y-2.5">
            {CURRENT.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-slate-300">
                <CheckCircle2 size={15} className="text-emerald-400 mt-0.5 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel className="p-5">
          <div className="text-sm font-medium text-cyan-300 mb-4">Future Roadmap</div>
          <ul className="space-y-2.5">
            {FUTURE.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-slate-400">
                <Circle size={13} className="text-slate-600 mt-1 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
