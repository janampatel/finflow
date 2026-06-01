"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { StatCard } from "@/components/stat-card";
import { LoadingState, ErrorState } from "@/components/states";
import { formatCompact, formatCurrency, formatNumber, formatPercent } from "@/lib/format";
import { Database, ShieldAlert, Users, DollarSign } from "lucide-react";

export default function OverviewPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["statistics"],
    queryFn: api.statistics,
  });

  return (
    <div>
      <header className="mb-8">
        <h1 className="text-2xl font-bold">Overview</h1>
        <p className="text-muted text-sm mt-1">
          Live statistics across the full transaction corpus.
        </p>
      </header>

      {isLoading && <LoadingState label="Loading statistics…" />}
      {error && <ErrorState message={(error as Error).message} />}

      {data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Total Transactions"
              value={formatCompact(data.total_transactions)}
              sub={formatNumber(data.total_transactions) + " rows"}
              icon={<Database size={16} />}
            />
            <StatCard
              label="Fraud Rate"
              value={formatPercent(data.fraud_rate_pct, 2)}
              sub={formatNumber(data.fraud_transactions) + " flagged"}
              accent="danger"
              icon={<ShieldAlert size={16} />}
            />
            <StatCard
              label="Unique Accounts"
              value={formatCompact(data.unique_users)}
              icon={<Users size={16} />}
            />
            <StatCard
              label="Avg Amount"
              value={formatCurrency(data.avg_amount)}
              sub={`max ${formatCompact(data.max_amount)}`}
              accent="success"
              icon={<DollarSign size={16} />}
            />
          </div>

          <section className="mt-8 bg-surface rounded-xl border border-border p-6">
            <h2 className="text-sm font-semibold mb-3">Architecture</h2>
            <pre className="text-xs text-muted leading-relaxed overflow-x-auto">
{`Next.js (stateless, CDN-cacheable)
   │  TanStack Query cache · virtualized tables
   ▼  HTTP
FastAPI (:8000)  ──▶  DuckDB / Parquet  ──▶  ${formatNumber(data.total_transactions)} transactions
   │
   ▼  Deterministic agent
Planner → Tools (FinBERT · PyOD · RapidFuzz · statsmodels) → Insight → Synthesis → Grounding ≥ 0.85`}
            </pre>
          </section>
        </>
      )}
    </div>
  );
}
