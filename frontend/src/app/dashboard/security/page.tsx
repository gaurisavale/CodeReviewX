import { ShieldCheck, Server, Lock, Database, Globe2 } from "lucide-react";
import { Panel } from "@/components/ui";

const ENTERPRISE_ITEMS = [
  {
    icon: Server,
    title: "On-Premise Deployment",
    body: "Run the structural analyzer and LLM interpretation layer entirely inside your own infrastructure.",
  },
  {
    icon: Lock,
    title: "Private Network Architecture",
    body: "No code ever leaves your VPC; the frontend and backend communicate over a private network only.",
  },
  {
    icon: Database,
    title: "Containerized Architecture",
    body: "Ship the FastAPI backend and Next.js frontend as separate containers, scaled independently.",
  },
  {
    icon: ShieldCheck,
    title: "Zero Data Exfiltration",
    body: "With a locally hosted LLM (or no LLM at all, via fallback mode), no source code is sent to a third party.",
  },
  {
    icon: Globe2,
    title: "Data Residency",
    body: "Pin analysis workloads to a specific region to meet residency requirements.",
  },
];

export default function SecurityPage() {
  return (
    <div className="p-6 sm:p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-50 mb-1">Security &amp; Privacy</h1>
      <p className="text-slate-500 text-sm mb-6">
        What this prototype does today, and what a production deployment would add.
      </p>

      <Panel className="p-5 mb-8 border-amber-500/20">
        <div className="text-sm font-medium text-amber-300 mb-2">Where code is processed right now</div>
        <p className="text-sm text-slate-400 leading-relaxed">
          In this MVP, submitted code is sent from your browser to the FastAPI backend
          you run locally, analyzed there with Python&apos;s <code className="mono text-slate-300">ast</code> module,
          and — only if you&apos;ve configured <code className="mono text-slate-300">ANTHROPIC_API_KEY</code> — a short
          snippet plus already-computed metrics are sent to the Claude API to generate
          an explanation. Without an API key, everything stays on your machine and a
          deterministic fallback explainer is used instead.
        </p>
      </Panel>

      <div className="text-sm font-medium text-slate-200 mb-3">
        Proposed enterprise deployment architecture
      </div>
      <p className="text-xs text-slate-600 mb-5">
        The items below describe a target production design — they are not guarantees
        of the current prototype&apos;s behavior.
      </p>
      <div className="grid sm:grid-cols-2 gap-4">
        {ENTERPRISE_ITEMS.map((item) => (
          <Panel key={item.title} className="p-5">
            <item.icon size={18} className="text-cyan-400 mb-3" />
            <div className="text-sm font-medium text-slate-100 mb-1.5">{item.title}</div>
            <div className="text-xs text-slate-500 leading-relaxed">{item.body}</div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
