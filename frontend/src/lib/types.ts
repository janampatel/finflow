// TypeScript types mirroring the FastAPI response contract.

export interface Transaction {
  step: number;
  type: string;
  amount: number;
  nameOrig: string;
  nameDest: string;
  oldbalanceOrg: number;
  newbalanceOrig: number;
  oldbalanceDest: number;
  newbalanceDest: number;
  isFraud: number;
  isFlaggedFraud: number;
}

export interface Pagination {
  offset: number;
  limit: number;
  total: number;
  returned: number;
}

export interface TransactionsResponse {
  data: Transaction[];
  pagination: Pagination;
}

export interface Statistics {
  total_transactions: number;
  fraud_transactions: number;
  fraud_rate_pct: number;
  avg_amount: number;
  min_amount: number;
  max_amount: number;
  unique_users: number;
}

// ---- Agent analyze contract ----

export interface AnalyzeTransactionInput {
  description: string;
  amount: number;
  balance_change: number;
  merchant: string;
  transaction_type?: string;
  balance_change_dest?: number;
}

export interface EnrichedResult {
  category: string;
  confidence: number;
  is_low_confidence: boolean;
  raw_description: string;
  all_scores?: Record<string, number>;
  tool: string;
}

export interface AnomalyResult {
  is_anomaly: boolean;
  anomaly_score: number;
  severity: string;
  anomaly_reason: string;
  method?: string;
  tool: string;
}

export interface FraudResult {
  fraud_probability: number;
  is_fraud_predicted: boolean;
  risk_level: string;
  method: string;
  tool: string;
}

export interface MerchantResult {
  raw_merchant: string;
  normalized_merchant: string;
  match_score: number;
  inferred_category: string;
  tool: string;
}

export interface CashflowResult {
  cash_flow_summary?: {
    total_income: number;
    total_expenses: number;
    net_cash_flow: number;
    transaction_count: number;
    avg_transaction: number;
    std_transaction: number;
    income_to_expense_ratio: number | null;
  };
  recurring_transactions?: unknown[];
  recurring_count?: number;
  total_transaction_count?: number;
  tool: string;
}

export interface Insights {
  health_score: number;
  components?: Record<string, number>;
  metrics?: {
    avg_confidence?: number;
    anomaly_rate?: number;
    num_categories?: number;
    num_transactions?: number;
  };
  insights?: string[];
  num_insights?: number;
  risk_level?: string;
  tool: string;
}

export interface AnalyzeResponse {
  final_response: string;
  grounding_score: number;
  execution_trace: string[];
  llm_grounding_score?: number;
  used_fallback?: boolean;
  enriched_results: EnrichedResult[];
  anomaly_results: AnomalyResult[];
  fraud_results: FraudResult[];
  merchant_results: MerchantResult[];
  cashflow_results: CashflowResult;
  insights: Insights;
}
