"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { api } from "@/lib/api";
import { StatCard } from "@/components/stat-card";
import { formatCurrency } from "@/lib/format";
import type { AnalyzeResponse, AnalyzeTransactionInput, Transaction } from "@/lib/types";
import { HeartPulse, Lightbulb } from "lucide-react";

function mapHistory(tx: Transaction): AnalyzeTransactionInput {
  return {
    description: `${tx.type} - ${tx.nameDest}`,
    amount: tx.amount,
    balance_change: tx.newbalanceOrig - tx.oldbalanceOrg,
    merchant: tx.nameDest || tx.nameOrig || "Unknown",
  };
}

// Normalize health score to a 0-100 scale (tool emits 0-1 or 0-100 depending on path).
function normScore(s: number): number {
  if (!Number.isFinite(s)) return 0;
  return s <= 1 ? s * 100 : s;
}

function scoreColor(s: number): string {
  if (s >= 70) return "#22c55e";
  if (s >= 40) return "#eab308";
  return "#ef4444";
}

export default function HealthPage() {
  const [userId, setUserId] = useState("C1462946854");

  const mut = useMutation<AnalyzeResponse>({
    mutationFn: async () => {
      const res = await api.transactions({ userId, limit: 30 });
      const txs = res.data.map(mapHistory);
      if (txs.length === 0) throw new Error("No transactions for this user.");
      return api.analyze(txs);
    },
  });

  const trace = mut.data;
  const score = trace ? normScore(trace.insights.health_score) : 0;
  const components = trace?.insights.components ?? {};
  const cashflow = trace?.cashflow_results.cash_flow_summary;
  const insightList = trace?.insights.insights ?? [];

  const gaugeData = [{ name: "health", value: score, fill: scoreColor(score) }];

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <HeartPulse size={22} /> Financial Health
        </h1>
        <p className="text-muted text-sm mt-1">
          Aggregated wellness score from the deterministic insight + cashflow tools.
        </p>
      </header>

      <section className="bg-surface rounded-xl border border-border p-5 mb-6">
        <div className="flex items-end gap-3 flex-wrap">
          <div>
            <label className="block text-xs text-muted mb-1">User ID</label>
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="bg-bg border border-border rounded-lg px-3 py-2 text-sm w-52 focus:outline-none focus:border-accent"
            />
          </div>
          <button
            onClick={() => mut.mutate()}
            disabled={mut.isPending}
            className="bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-accent/90 disabled:opacity-50"
          >
            {mut.isPending ? "Analyzing…" : "Compute Health"}
          </button>
          {mut.error && <span className="text-sm text-danger pb-2">{(mut.error as Error).message}</span>}
        </div>
      </section>

      {trace && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
            {/* Gauge */}
            <div className="bg-surface rounded-xl border border-border p-5 flex flex-col items-center">
              <h3 className="text-sm font-semibold mb-2 self-start">Health Score</h3>
              <ResponsiveContainer width="100%" height={220}>
                <RadialBarChart
                  innerRadius="70%"
                  outerRadius="100%"
                  data={gaugeData}
                  startAngle={210}
                  endAngle={-30}
                >
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar background={{ fill: "#1a2235" }} dataKey="value" cornerRadius={8} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="-mt-28 text-center">
                <div className="text-4xl font-bold" style={{ color: scoreColor(score) }}>
                  {score.toFixed(0)}
                </div>
                <div className="text-xs text-muted">out of 100</div>
              </div>
              <div className="mt-20 text-sm text-muted">
                Risk: <span className="text-gray-200">{trace.insights.risk_level ?? "—"}</span>
              </div>
            </div>

            {/* Components + cashflow */}
            <div className="space-y-4">
              <div className="bg-surface rounded-xl border border-border p-5">
                <h3 className="text-sm font-semibold mb-4">Score Components</h3>
                <div className="space-y-3">
                  {Object.entries(components).map(([k, v]) => {
                    const pct = normScore(v as number);
                    return (
                      <div key={k}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-muted">{k.replace(/_/g, " ")}</span>
                          <span>{pct.toFixed(0)}</span>
                        </div>
                        <div className="h-2 rounded-full bg-surface2 overflow-hidden">
                          <div
                            className="h-full bg-accent"
                            style={{ width: `${Math.min(100, pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  {Object.keys(components).length === 0 && (
                    <span className="text-sm text-muted">No component breakdown available.</span>
                  )}
                </div>
              </div>

              {cashflow && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatCard label="Income" value={formatCurrency(cashflow.total_income)} accent="success" />
                  <StatCard label="Expenses" value={formatCurrency(cashflow.total_expenses)} accent="warning" />
                  <StatCard
                    label="Net Flow"
                    value={formatCurrency(cashflow.net_cash_flow)}
                    accent={cashflow.net_cash_flow >= 0 ? "success" : "danger"}
                  />
                  <StatCard label="Avg Txn" value={formatCurrency(cashflow.avg_transaction)} />
                </div>
              )}
            </div>
          </div>

          {/* Insights */}
          {insightList.length > 0 && (
            <div className="bg-surface rounded-xl border border-border p-5">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Lightbulb size={15} /> Insights
              </h3>
              <ul className="space-y-2">
                {insightList.map((ins, i) => (
                  <li key={i} className="text-sm text-gray-200 flex gap-2">
                    <span className="text-accent">•</span> {ins}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
