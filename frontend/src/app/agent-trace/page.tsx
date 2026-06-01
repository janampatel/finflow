"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { GroundingGauge } from "@/components/grounding-gauge";
import { StatCard } from "@/components/stat-card";
import { formatCurrency } from "@/lib/format";
import type { AnalyzeResponse, AnalyzeTransactionInput, Transaction } from "@/lib/types";
import { Bot, Download, Play, Wrench, Sparkles, ShieldCheck } from "lucide-react";

const TX_TYPES = ["DEBIT", "CASH_OUT", "PAYMENT", "TRANSFER", "CASH_IN"];

function mapHistory(tx: Transaction): AnalyzeTransactionInput {
  return {
    description: `${tx.type} - ${tx.nameDest}`,
    amount: tx.amount,
    balance_change: tx.newbalanceOrig - tx.oldbalanceOrg,
    balance_change_dest: tx.newbalanceDest - tx.oldbalanceDest,
    merchant: tx.nameDest || tx.nameOrig || "Unknown",
    transaction_type: tx.type,
  };
}

export default function AgentTracePage() {
  const [userId, setUserId] = useState("C1462946854");
  const [history, setHistory] = useState<Transaction[] | null>(null);

  const [desc, setDesc] = useState("AMZN MKTPLC");
  const [amount, setAmount] = useState(100);
  const [type, setType] = useState("DEBIT");

  const historyMut = useMutation({
    mutationFn: () => api.transactions({ userId, limit: 30 }),
    onSuccess: (res) => setHistory(res.data),
  });

  const analyzeMut = useMutation<AnalyzeResponse>({
    mutationFn: () => {
      const txs: AnalyzeTransactionInput[] = (history ?? []).map(mapHistory);
      txs.push({
        description: desc,
        amount,
        balance_change: ["CASH_OUT", "DEBIT", "PAYMENT"].includes(type) ? -amount : amount,
        balance_change_dest: 0,
        merchant: desc.split(" ")[0] || "Unknown",
        transaction_type: type,
      });
      return api.analyze(txs);
    },
  });

  const trace = analyzeMut.data;
  const txCount = (history?.length ?? 0) + 1;

  function downloadTrace() {
    if (!trace) return;
    const blob = new Blob([JSON.stringify(trace, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agent_trace_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Bot size={22} /> Agent Execution Trace
        </h1>
        <p className="text-muted text-sm mt-1">
          Runs the deterministic agent on the user&apos;s history + a new transaction.
        </p>
      </header>

      {/* Step 1: history */}
      <section className="bg-surface rounded-xl border border-border p-5 mb-4">
        <h2 className="text-sm font-semibold mb-3">1 · Load user history</h2>
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
            onClick={() => historyMut.mutate()}
            disabled={historyMut.isPending}
            className="bg-accent/15 text-accent border border-accent/30 rounded-lg px-4 py-2 text-sm hover:bg-accent/25 disabled:opacity-50"
          >
            {historyMut.isPending ? "Loading…" : "Load History"}
          </button>
          {history && (
            <span className="text-sm text-success pb-2">
              ✓ {history.length} transactions loaded
            </span>
          )}
          {historyMut.error && (
            <span className="text-sm text-danger pb-2">{(historyMut.error as Error).message}</span>
          )}
        </div>
      </section>

      {/* Step 2: new transaction */}
      <section className="bg-surface rounded-xl border border-border p-5 mb-4">
        <h2 className="text-sm font-semibold mb-3">2 · New transaction to analyze</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-muted mb-1">Description</label>
            <input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1">Amount</label>
            <input
              type="number"
              value={amount}
              min={0.01}
              step={0.01}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1">Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            >
              {TX_TYPES.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Step 3: run */}
      <section className="mb-6">
        {!history && (
          <p className="text-sm text-warning mb-3">
            ⚠ Load user history first for meaningful, grounded insights.
          </p>
        )}
        <button
          onClick={() => analyzeMut.mutate()}
          disabled={!history || analyzeMut.isPending}
          className="flex items-center gap-2 bg-accent text-white rounded-lg px-5 py-2.5 text-sm font-medium hover:bg-accent/90 disabled:opacity-50"
        >
          <Play size={16} />
          {analyzeMut.isPending ? "Running pipeline…" : "Run Agent Pipeline"}
        </button>
        {analyzeMut.error && (
          <p className="text-sm text-danger mt-3">{(analyzeMut.error as Error).message}</p>
        )}
      </section>

      {/* Results */}
      {trace && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-4">
            <GroundingGauge score={trace.grounding_score} />
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Transactions" value={txCount} />
              <StatCard label="Exec Nodes" value={trace.execution_trace.length} />
              <StatCard
                label="Tools Run"
                value={
                  trace.enriched_results.length +
                  trace.anomaly_results.length +
                  trace.merchant_results.length
                }
              />
            </div>
          </div>

          {txCount < 10 && (
            <div className="bg-warning/10 border border-warning/30 text-warning rounded-lg px-4 py-3 text-sm">
              Limited data ({txCount} transactions). Pattern-level insights are suppressed by design —
              the grounding guard rejects diversity/pattern claims below 10 transactions.
            </div>
          )}

          {/* Execution path */}
          <div className="bg-surface rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold mb-3">Execution Path</h3>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {trace.execution_trace.map((node, i) => (
                <span key={i} className="flex items-center gap-2">
                  <span className="bg-surface2 border border-border rounded-full px-3 py-1">
                    {node}
                  </span>
                  {i < trace.execution_trace.length - 1 && <span className="text-muted">→</span>}
                </span>
              ))}
            </div>
          </div>

          {/* Tools */}
          <div className="bg-surface rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Wrench size={15} /> Tool Outputs (last transaction)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ToolBlock title="Enrichment · FinBERT">
                {(() => {
                  const e = trace.enriched_results.at(-1);
                  return e ? (
                    <>
                      <Row k="Category" v={e.category} />
                      <Row k="Confidence" v={`${(e.confidence * 100).toFixed(1)}%`} />
                      <Row k="Low confidence" v={e.is_low_confidence ? "yes" : "no"} />
                    </>
                  ) : (
                    <span className="text-muted">—</span>
                  );
                })()}
              </ToolBlock>

              <ToolBlock title="Anomaly · PyOD">
                {(() => {
                  const a = trace.anomaly_results.at(-1);
                  return a ? (
                    <>
                      <Row k="Anomaly" v={a.is_anomaly ? "● yes" : "no"} danger={a.is_anomaly} />
                      <Row k="Score" v={a.anomaly_score.toFixed(2)} />
                      <Row k="Severity" v={a.severity} />
                      <Row k="Reason" v={a.anomaly_reason} />
                    </>
                  ) : (
                    <span className="text-muted">—</span>
                  );
                })()}
              </ToolBlock>

              <ToolBlock title="Fraud · RandomForest (supervised)">
                {(() => {
                  const f = trace.fraud_results?.at(-1);
                  if (!f) return <span className="text-muted">— (not routed)</span>;
                  const pct = (f.fraud_probability <= 1 ? f.fraud_probability * 100 : f.fraud_probability);
                  return (
                    <>
                      <Row k="Fraud probability" v={`${pct.toFixed(1)}%`} danger={f.is_fraud_predicted} />
                      <Row k="Predicted fraud" v={f.is_fraud_predicted ? "● yes" : "no"} danger={f.is_fraud_predicted} />
                      <Row k="Risk level" v={f.risk_level} />
                    </>
                  );
                })()}
              </ToolBlock>

              <ToolBlock title="Merchant · RapidFuzz">
                {(() => {
                  const m = trace.merchant_results.at(-1);
                  const score = m ? (m.match_score <= 1 ? m.match_score * 100 : m.match_score) : 0;
                  return m ? (
                    <>
                      <Row k="Name" v={m.normalized_merchant} />
                      <Row k="Match" v={`${score.toFixed(0)}%`} />
                      <Row k="Category" v={m.inferred_category} />
                    </>
                  ) : (
                    <span className="text-muted">—</span>
                  );
                })()}
              </ToolBlock>

              <ToolBlock title="Insight · Health">
                <Row k="Health score" v={(trace.insights.health_score ?? 0).toFixed(2)} />
                <Row k="Transactions" v={trace.insights.metrics?.num_transactions ?? txCount} />
                {trace.cashflow_results.cash_flow_summary && (
                  <Row
                    k="Net cash flow"
                    v={formatCurrency(trace.cashflow_results.cash_flow_summary.net_cash_flow)}
                  />
                )}
              </ToolBlock>
            </div>
          </div>

          {/* Synthesis */}
          <div className="bg-surface rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Sparkles size={15} /> Synthesis (LLM narrative)
            </h3>
            <p className="text-sm leading-relaxed text-gray-200 italic">
              &ldquo;{trace.final_response}&rdquo;
            </p>
          </div>

          {/* Validation + download */}
          <div className="bg-surface rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <ShieldCheck size={15} /> Hallucination Guard
            </h3>
            <p className="text-sm text-muted mb-4">
              Extracts numbers/terms from the narrative and checks each against tool outputs
              (±tolerance). Score = traceable claims ÷ total claims.
            </p>
            <button
              onClick={downloadTrace}
              className="flex items-center gap-2 bg-surface2 border border-border rounded-lg px-4 py-2 text-sm hover:bg-border/40"
            >
              <Download size={15} /> Download trace JSON
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ToolBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-bg rounded-lg border border-border p-4">
      <div className="text-xs font-semibold text-accent mb-2">{title}</div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Row({ k, v, danger }: { k: string; v: React.ReactNode; danger?: boolean }) {
  return (
    <div className="flex justify-between gap-3 text-sm">
      <span className="text-muted">{k}</span>
      <span className={danger ? "text-danger font-medium text-right" : "text-right"}>{v}</span>
    </div>
  );
}
