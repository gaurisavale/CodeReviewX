import Link from "next/link";
import {
  CircuitBoard,
  ArrowRight,
  ScanSearch,
  Sparkles,
  Waypoints,
  Wrench,
} from "lucide-react";

function MiniGraph() {
  const nodes = [
    { x: 220, y: 30, r: "healthy", label: "main()" },
    { x: 90, y: 130, r: "critical", label: "process_order()" },
    { x: 350, y: 130, r: "healthy", label: "calculate_total()" },
    { x: 90, y: 230, r: "warning", label: "validate_order()" },
    { x: 220, y: 230, r: "healthy", label: "save_order()" },
  ];
  const edges: [number, number][] = [
    [0, 1],
    [0, 2],
    [1, 3],
    [0, 4],
  ];
  const color = (r: string) =>
    r === "critical" ? "#ef4444" : r === "warning" ? "#f59e0b" : "#10b981";

  return (
    <svg viewBox="0 0 440 280" className="w-full h-full">
      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a].x}
          y1={nodes[a].y}
          x2={nodes[b].x}
          y2={nodes[b].y}
          stroke="#1e2a44"
          strokeWidth={1.5}
        />
      ))}
      {nodes.map((n, i) => (
        <g key={i}>
          <circle
            cx={n.x}
            cy={n.y}
            r={i === 1 ? 30 : 22}
            fill="#0b0f18"
            stroke={color(n.r)}
            strokeWidth={2}
            opacity={0.9}
          />
          {i === 1 && (
            <circle cx={n.x} cy={n.y} r={30} fill="none" stroke={color(n.r)} strokeWidth={1} opacity={0.4}>
              <animate attributeName="r" values="30;40;30" dur="2.4s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.4;0;0.4" dur="2.4s" repeatCount="indefinite" />
            </circle>
          )}
          <text
            x={n.x}
            y={n.y + (i === 1 ? 46 : 38)}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize="10"
            fontFamily="monospace"
          >
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

const HOW_IT_WORKS = [
  {
    icon: ScanSearch,
    title: "Structural Analysis",
    body: "A real Python AST analyzer measures complexity, nesting, function length, and parameters — deterministic numbers, never guessed.",
  },
  {
    icon: Sparkles,
    title: "Explainable AI",
    body: "The AI never invents a metric. It interprets the verified structural data and explains, in plain language, why a function is risky.",
  },
  {
    icon: Waypoints,
    title: "Interactive Visualization",
    body: "Every function becomes a node in a live health graph — colored by risk, connected by real call relationships.",
  },
  {
    icon: Wrench,
    title: "Refactoring Recommendations",
    body: "Concrete, metric-grounded suggestions for how to split, flatten, or simplify the functions that need it most.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex-1 bg-[#05070d]">
      <header className="flex items-center justify-between px-6 sm:px-10 h-16 border-b border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center">
            <CircuitBoard size={18} className="text-slate-950" />
          </div>
          <span className="text-sm font-semibold text-slate-100">CodeReviewX</span>
        </div>
        <Link
          href="/dashboard"
          className="text-sm text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 rounded-lg px-4 py-1.5 transition-colors"
        >
          Enter Dashboard
        </Link>
      </header>

      <section className="max-w-6xl mx-auto px-6 sm:px-10 pt-20 pb-16 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <div className="inline-flex items-center gap-2 text-xs text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 rounded-full px-3 py-1 mb-6">
            <Sparkles size={12} /> Explainable AI for Code Health
          </div>
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-slate-50 leading-[1.1]">
            Understand Your Code.
            <br />
            Not Just Your Score.
          </h1>
          <p className="mt-6 text-slate-400 text-lg leading-relaxed max-w-lg">
            CodeReviewX combines structural code analysis with Explainable AI to
            reveal why your code is difficult to maintain.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/dashboard/analyze"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 font-medium rounded-xl px-5 py-2.5 hover:brightness-110 transition-all shadow-[0_0_24px_rgba(34,211,238,0.25)]"
            >
              Analyze Code <ArrowRight size={16} />
            </Link>
            <Link
              href="/dashboard/analyze?demo=1"
              className="inline-flex items-center gap-2 border border-slate-700 text-slate-200 rounded-xl px-5 py-2.5 hover:border-slate-500 hover:bg-slate-800/40 transition-colors"
            >
              View Demo
            </Link>
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-6 h-80">
          <div className="text-xs text-slate-500 mb-2 mono">function_health_graph.tsx</div>
          <MiniGraph />
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 sm:px-10 py-16 border-t border-slate-800/60">
        <h2 className="text-2xl font-semibold text-slate-100 mb-2">How It Works</h2>
        <p className="text-slate-500 mb-10 max-w-2xl">
          Structural analysis is the source of truth. The AI is only the interpreter.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {HOW_IT_WORKS.map((f) => (
            <div key={f.title} className="glass-panel rounded-2xl p-5">
              <f.icon size={20} className="text-cyan-400 mb-3" />
              <div className="text-sm font-medium text-slate-100 mb-2">{f.title}</div>
              <div className="text-sm text-slate-500 leading-relaxed">{f.body}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-slate-800/60 py-14 text-center">
        <p className="text-slate-400 text-lg">
          Built for developers who want{" "}
          <span className="text-slate-100 font-medium">answers</span>, not just{" "}
          <span className="text-slate-100 font-medium">warnings</span>.
        </p>
      </section>
    </div>
  );
}
