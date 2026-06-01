"use client";

import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { VirtualTable, type Column } from "@/components/virtual-table";
import { StatCard } from "@/components/stat-card";
import { LoadingState, ErrorState, EmptyState } from "@/components/states";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { Transaction } from "@/lib/types";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";

const TX_TYPES = ["All", "CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"];
const PAGE_SIZES = [50, 100, 250, 500];

export default function TransactionsPage() {
  const [userId, setUserId] = useState("");
  const [userIdInput, setUserIdInput] = useState("");
  const [txType, setTxType] = useState("All");
  const [pageSize, setPageSize] = useState(100);
  const [page, setPage] = useState(0);

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["transactions", { userId, txType, pageSize, page }],
    queryFn: () =>
      api.transactions({
        userId: userId || undefined,
        txType,
        limit: pageSize,
        offset: page * pageSize,
      }),
    placeholderData: keepPreviousData,
  });

  const rows = data?.data ?? [];
  const total = data?.pagination.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const fraudInView = rows.filter((r) => r.isFraud === 1).length;
  const debit = rows
    .filter((r) => ["CASH_OUT", "DEBIT", "PAYMENT"].includes(r.type))
    .reduce((s, r) => s + r.amount, 0);

  const columns: Column<Transaction>[] = [
    { key: "step", header: "Step", width: 70, align: "right", render: (r) => r.step },
    {
      key: "type",
      header: "Type",
      width: 110,
      render: (r) => <span className="text-accent">{r.type}</span>,
    },
    {
      key: "amount",
      header: "Amount",
      width: 140,
      align: "right",
      render: (r) => formatCurrency(r.amount),
    },
    { key: "nameOrig", header: "Origin", width: 150, render: (r) => r.nameOrig },
    { key: "nameDest", header: "Destination", width: 150, render: (r) => r.nameDest },
    {
      key: "balance",
      header: "Δ Balance (orig)",
      width: 150,
      align: "right",
      render: (r) => formatCurrency(r.newbalanceOrig - r.oldbalanceOrg),
    },
    {
      key: "isFraud",
      header: "Fraud",
      width: 90,
      align: "center",
      render: (r) =>
        r.isFraud === 1 ? (
          <span className="text-danger font-medium">● Yes</span>
        ) : (
          <span className="text-muted">No</span>
        ),
    },
  ];

  function applyUserFilter() {
    setUserId(userIdInput.trim());
    setPage(0);
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Transaction Explorer</h1>
        <p className="text-muted text-sm mt-1">
          Server-paginated over the full corpus · virtualized rendering.
        </p>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total (filtered)" value={formatNumber(total)} />
        <StatCard label="In View" value={formatNumber(rows.length)} />
        <StatCard label="Fraud in View" value={fraudInView} accent={fraudInView ? "danger" : "default"} />
        <StatCard label="Debits in View" value={formatCurrency(debit)} accent="warning" />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="flex items-end gap-2">
          <div>
            <label className="block text-xs text-muted mb-1">User ID</label>
            <input
              value={userIdInput}
              onChange={(e) => setUserIdInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applyUserFilter()}
              placeholder="e.g. C1462946854"
              className="bg-surface border border-border rounded-lg px-3 py-2 text-sm w-48 focus:outline-none focus:border-accent"
            />
          </div>
          <button
            onClick={applyUserFilter}
            className="flex items-center gap-1.5 bg-accent/15 text-accent border border-accent/30 rounded-lg px-3 py-2 text-sm hover:bg-accent/25"
          >
            <Search size={15} /> Filter
          </button>
        </div>

        <div>
          <label className="block text-xs text-muted mb-1">Type</label>
          <select
            value={txType}
            onChange={(e) => {
              setTxType(e.target.value);
              setPage(0);
            }}
            className="bg-surface border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
          >
            {TX_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-muted mb-1">Page Size</label>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(0);
            }}
            className="bg-surface border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
          >
            {PAGE_SIZES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {isFetching && <span className="text-xs text-muted pb-2">updating…</span>}
      </div>

      {/* Table */}
      {isLoading ? (
        <LoadingState label="Loading transactions…" />
      ) : error ? (
        <ErrorState message={(error as Error).message} />
      ) : rows.length === 0 ? (
        <EmptyState>No transactions match these filters.</EmptyState>
      ) : (
        <>
          <VirtualTable
            rows={rows}
            columns={columns}
            rowKey={(_, i) => i}
            height={560}
          />

          {/* Pagination */}
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
