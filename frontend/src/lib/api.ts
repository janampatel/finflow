// Typed API client for the FinFlow FastAPI backend.

import type {
  AnalyzeResponse,
  AnalyzeTransactionInput,
  Statistics,
  TransactionsResponse,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export interface TransactionsQuery {
  userId?: string;
  limit?: number;
  offset?: number;
  txType?: string;
}

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),

  statistics: () => request<Statistics>("/api/statistics"),

  transactions: (q: TransactionsQuery = {}) => {
    const params = new URLSearchParams();
    if (q.userId) params.set("user_id", q.userId);
    if (q.limit != null) params.set("limit", String(q.limit));
    if (q.offset != null) params.set("offset", String(q.offset));
    if (q.txType && q.txType !== "All") params.set("tx_type", q.txType);
    const qs = params.toString();
    return request<TransactionsResponse>(`/api/transactions${qs ? `?${qs}` : ""}`);
  },

  fraudTransactions: (limit = 100, offset = 0) =>
    request<TransactionsResponse>(
      `/api/fraud-transactions?limit=${limit}&offset=${offset}`
    ),

  analyze: (transactions: AnalyzeTransactionInput[]) =>
    request<AnalyzeResponse>("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ transactions }),
    }),
};

export { BASE_URL };
