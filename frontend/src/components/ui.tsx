import { RiskLevel } from "@/lib/types";
import clsx from "clsx";

export function riskColor(risk: RiskLevel | "critical" | "warning" | "info"): string {
  switch (risk) {
    case "high":
    case "critical":
      return "#ef4444";
    case "medium":
    case "warning":
      return "#f59e0b";
    case "low":
      return "#10b981";
    case "info":
      return "#38bdf8";
    default:
      return "#22d3ee";
  }
}

export function RiskBadge({ risk }: { risk: RiskLevel }) {
  const label = risk === "high" ? "High Risk" : risk === "medium" ? "Medium Risk" : "Low Risk";
  const cls =
    risk === "high"
      ? "bg-red-500/10 text-red-400 border-red-500/30"
      : risk === "medium"
      ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-medium", cls)}>
      {label}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: "critical" | "warning" | "info" }) {
  const cls =
    severity === "critical"
      ? "bg-red-500/10 text-red-400 border-red-500/30"
      : severity === "warning"
      ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
      : "bg-sky-500/10 text-sky-300 border-sky-500/30";
  return (
    <span className={clsx("text-[11px] tracking-wide uppercase px-2 py-0.5 rounded-full border font-semibold", cls)}>
      {severity}
    </span>
  );
}

export function StatusDot({ online }: { online: boolean }) {
  return (
    <span className="relative flex h-2 w-2">
      <span
        className={clsx(
          "absolute inline-flex h-full w-full rounded-full opacity-75 pulse-dot",
          online ? "bg-emerald-400" : "bg-red-400"
        )}
      />
      <span
        className={clsx("relative inline-flex rounded-full h-2 w-2", online ? "bg-emerald-400" : "bg-red-400")}
      />
    </span>
  );
}

export function ProgressBar({
  value,
  colorClass = "bg-cyan-400",
}: {
  value: number;
  colorClass?: string;
}) {
  return (
    <div className="w-full h-2 rounded-full bg-slate-800/80 overflow-hidden">
      <div
        className={clsx("h-full rounded-full transition-all duration-700", colorClass)}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function scoreColorClass(value: number): string {
  if (value >= 75) return "bg-emerald-400";
  if (value >= 50) return "bg-amber-400";
  return "bg-red-400";
}

export function scoreTextColor(value: number): string {
  if (value >= 75) return "text-emerald-400";
  if (value >= 50) return "text-amber-400";
  return "text-red-400";
}

export function Panel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={clsx("glass-panel rounded-2xl", className)}>{children}</div>;
}

export function scoreHex(value: number): string {
  if (value >= 75) return "#10b981";
  if (value >= 50) return "#f59e0b";
  return "#ef4444";
}
