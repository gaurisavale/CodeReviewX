"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { CircuitBoard, Settings, User, Globe } from "lucide-react";
import { StatusDot } from "./ui";
import { fetchEngineStatus } from "@/lib/api";
import clsx from "clsx";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/history", label: "Analysis History" },
  { href: "/dashboard/roadmap", label: "Documentation" },
];

export default function Navbar() {
  const pathname = usePathname();
  const [online, setOnline] = useState(true);

  useEffect(() => {
    let mounted = true;
    fetchEngineStatus().then((status) => {
      if (mounted) setOnline(status.ai_engine !== "offline");
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/70 bg-[#05070d]/90 backdrop-blur">
      <div className="flex items-center justify-between px-6 h-16">
        <div className="flex items-center gap-8">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center shadow-[0_0_18px_rgba(34,211,238,0.35)]">
              <CircuitBoard size={18} className="text-slate-950" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-tight text-slate-100">CodeReviewX</div>
              <div className="text-[10px] text-slate-500 -mt-0.5">AI Code Health</div>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  "text-sm px-3 py-1.5 rounded-lg transition-colors",
                  pathname === link.href
                    ? "text-slate-100 bg-slate-800/60"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/30"
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 bg-slate-900/60 border border-slate-800 rounded-full px-3 py-1.5">
            <StatusDot online={online} />
            AI Review Engine: {online ? "Online" : "Offline"}
          </div>
          <button
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            title="Language"
          >
            <Globe size={16} />
          </button>
          <button
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            title="Settings"
          >
            <Settings size={16} />
          </button>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
            <User size={15} className="text-slate-950" />
          </div>
        </div>
      </div>
    </header>
  );
}
