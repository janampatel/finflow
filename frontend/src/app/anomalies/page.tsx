"use client";

import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { api } from "@/lib/api";
import { VirtualTable, type Column } from "@/components/virtual-table";
import { StatCard } from "@/components/stat-card";
import { LoadingState, ErrorState, EmptyState } from "@/components/states";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { Transaction } from "@/lib/types";
import { ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 200;

export default function AnomaliesPage() {
  const [page, setPage] = useState(0);

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["fraud", page],
    queryFn: () => api.fraudTransactions(PAGE_SIZE, page * PAGE_SIZE),
    placeholderData: keepPreviousData,
  });

  const rows = data?.data ?? [];
  const total = data?.pagination.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const totalAmount = rows.reduce((s, r) => s + r.amount, 0);

  // Distribution by transaction type (fraud is concentrated in TRANSFER/CASH_OUT)
  const byType = Object.entries(
    rows.reduce<Record<string, number>>((acc, r) => {
      acc[r.type] = (acc[r.type] || 0) + 1;
      return acc;
    }, {})
  ).map(([type, count]) => ({ type, count }));

  const typeColors: Record<string, string> = {
    TRANSFER: "#ef4444",
    CASH_OUT: "#eab308",
    DEBIT: "#3b82f6",
    PAYMENT: "#22c55e",
    CASH_IN: "#8b5cf6",
  };

  const columns: Column<Transaction>[] = [
    { key: "step", header: "Step", width: 70, align: "right", render: (r) => r.step },
    { key: "type", header: "Type", width: 110, render: (r) => <span className="text-danger">{r.type}</span> },
    { key: "amount", header: "Amount", width: 150, align: "right", render: (r) => formatCurrency(r.amount) },
    { key: "nameOrig", header: "Origin", width: 150, render: (r) => r.nameOrig },
    { key: "nameDest", header: "Destination", width: 150, render: (r) => r.nameDest },
    {
      key: "flagged",
      header: "System Flagged",
      width: 130,
      align: "center",
      render: (r) =>
        r.isFlaggedFraud === 1 ? (
          <span className="text-warning">⚑ Flagged</span>
        ) : (
          <span className="text-muted">missed</span>
        ),
    },
  ];

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Anomaly Feed</h1>
        <p className="text-muted text-sm mt-1">
          Ground-truth fraudulent transactions (isFraud = 1), ranked by amount.
        </p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Fraud" value={formatNumber(total)} accent="danger" />
        <StatCard label="In View" value={formatNumber(rows.length)} />
        <StatCard label="Amount in View" value={formatCurrency(totalAmount)} accent="warning" />
        <StatCard
          label="System Caught"
          value={`${rows.filter((r) => r.isFlaggedFraud === 1).length}/${rows.length}`}
        />
      </div>

      {isLoading ? (
        <LoadingState label="Loading fraud transactions…" />
      ) : error ? (
        <ErrorState message={(error as Error).message} />
      ) : rows.length === 0 ? (
        <EmptyState>No fraudulent transactions found.</EmptyState>
      ) : (
        <>
          <div className="bg-surface rounded-xl border border-border p-5 mb-6">
            <h3 className="text-sm font-semibold mb-4">Fraud by Transaction Type (in view)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byType}>
                <XAxis dataKey="type" stroke="#8a94a8" fontSize={12} />
                <YAxis stroke="#8a94a8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: "#121826",
                    border: "1px solid #26304a",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {byType.map((entry) => (
                    <Cell key={entry.type} fill={typeColors[entry.type] || "#3b82f6"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {isFetching && <div className="text-xs text-muted mb-2">updating…</div>}

          <VirtualTable rows={rows} columns={columns} rowKey={(_, i) => i} height={520} />

          <div className="flex items-center justify-between mt-4 text-sm">
            <span className="text-muted">
              Page {page + 1} of {formatNumber(totalPages)}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="flex items-center gap-1 bg-surface border border-border rounded-lg px-3 py-1.5 disabled:opacity-40 hover:bg-surface2"
              >
                <ChevronLeft size={15} /> Prev
              </button>
              <button
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                className="flex items-center gap-1 bg-surface border border-border rounded-lg px-3 py-1.5 disabled:opacity-40 hover:bg-surface2"
              >
                Next <ChevronRight size={15} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
