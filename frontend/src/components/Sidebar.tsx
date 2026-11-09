"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  FilePlus2,
  History,
  FolderKanban,
  ShieldCheck,
  Map,
  Settings,
  BarChart3,
  GitBranch,
  Brain,
} from "lucide-react";
import clsx from "clsx";
import { StatusDot } from "./ui";
import { fetchEngineStatus } from "@/lib/api";

const ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/analyze", label: "New Analysis", icon: FilePlus2 },
  { href: "/dashboard/repo", label: "Repo Scan", icon: GitBranch },
  { href: "/dashboard/metrics", label: "Metrics", icon: BarChart3 },
  { href: "/dashboard/model", label: "ML Model", icon: Brain },
  { href: "/dashboard/history", label: "History", icon: History },
  { href: "/dashboard/projects", label: "Projects", icon: FolderKanban },
  { href: "/dashboard/security", label: "Security", icon: ShieldCheck },
  { href: "/dashboard/roadmap", label: "Roadmap", icon: Map },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<Record<string, string>>({
    structural_scanner: "online",
    ai_engine: "online",
    analysis_api: "online",
  });

  useEffect(() => {
    fetchEngineStatus().then(setStatus);
  }, []);

  return (
    <aside className="hidden lg:flex flex-col w-60 shrink-0 border-r border-slate-800/70 bg-[#070a12] px-3 py-5 gap-1">
      {ITEMS.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              active
                ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/20"
                : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 border border-transparent"
            )}
          >
            <Icon size={16} />
            {item.label}
          </Link>
        );
      })}

      <div className="mt-4 pt-4 border-t border-slate-800/70">
        <Link
          href="/dashboard/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 transition-colors"
        >
          <Settings size={16} />
          Settings
        </Link>
      </div>

      <div className="mt-auto pt-5">
        <div className="text-[11px] uppercase tracking-wider text-slate-500 px-3 mb-2">
          System Status
        </div>
        <div className="space-y-2 px-3">
          <StatusRow label="Structural Scanner" value={status.structural_scanner} />
          <StatusRow label="AI Engine" value={status.ai_engine} />
          <StatusRow label="Analysis API" value={status.analysis_api} />
        </div>
      </div>
    </aside>
  );
}

function StatusRow({ label, value }: { label: string; value?: string }) {
  const online = (value ?? "online").startsWith("online");
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-500">{label}</span>
      <span className={clsx("flex items-center gap-1.5", online ? "text-emerald-400" : "text-red-400")}>
        <StatusDot online={online} />
        {online ? "Online" : "Offline"}
      </span>
    </div>
  );
}
