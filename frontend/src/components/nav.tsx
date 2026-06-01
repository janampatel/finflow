"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Receipt, AlertTriangle, HeartPulse, Bot } from "lucide-react";
import clsx from "clsx";

const links = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: Receipt },
  { href: "/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/health", label: "Financial Health", icon: HeartPulse },
  { href: "/agent-trace", label: "Agent Trace", icon: Bot },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 border-r border-border bg-surface min-h-screen flex flex-col">
      <div className="px-5 py-5 border-b border-border">
        <div className="text-lg font-bold tracking-tight">💳 FinFlow</div>
        <div className="text-xs text-muted mt-0.5">Transaction Intelligence</div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                active
                  ? "bg-accent/15 text-white font-medium"
                  : "text-muted hover:bg-surface2 hover:text-white"
              )}
            >
              <Icon size={17} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 text-[11px] text-muted border-t border-border">
        Deterministic agent · grounding ≥ 0.85
      </div>
    </aside>
  );
}
