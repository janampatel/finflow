import type { ReactNode } from "react";
import clsx from "clsx";

interface StatCardProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: "default" | "success" | "warning" | "danger";
  icon?: ReactNode;
}

const accentMap = {
  default: "border-border",
  success: "border-l-success",
  warning: "border-l-warning",
  danger: "border-l-danger",
};

export function StatCard({ label, value, sub, accent = "default", icon }: StatCardProps) {
  return (
    <div
      className={clsx(
        "bg-surface rounded-xl border border-border p-5 border-l-4",
        accentMap[accent]
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
        {icon && <span className="text-muted">{icon}</span>}
      </div>
      <div className="text-2xl font-bold mt-2">{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}
