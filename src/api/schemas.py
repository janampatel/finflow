"""Pydantic schemas for API requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class Transaction(BaseModel):
    """Single transaction input."""

    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Transaction amount")
    balance_change: float = Field(..., description="Balance change (origin)")
    merchant: str = Field(..., description="Merchant name")
    transaction_type: Optional[str] = Field("", description="Type: TRANSFER/CASH_OUT/PAYMENT/... (improves fraud features)")
    balance_change_dest: Optional[float] = Field(0.0, description="Balance change at destination (for fraud features)")


class AnalyzeRequest(BaseModel):
    """Request to analyze transactions."""

    transactions: List[Transaction] = Field(..., description="List of transactions to analyze")


class ToolResult(BaseModel):
    """Result from a single tool."""

    tool_name: str
    success: bool
    data: Dict[str, Any] = {}


class AnalyzeResponse(BaseModel):
    """Response from agent analysis."""

    final_response: str = Field(..., description="Agent's narrative response (served)")
    grounding_score: float = Field(..., ge=0.0, le=1.0, description="Grounding of the served response")
    llm_grounding_score: float = Field(1.0, ge=0.0, le=1.0, description="Grounding of the raw LLM narrative before any fallback")
    used_fallback: bool = Field(False, description="True if the LLM narrative failed grounding and a deterministic summary was served")
    execution_trace: List[str] = Field(..., description="Execution nodes in order")

    enriched_results: List[Dict[str, Any]] = []
    anomaly_results: List[Dict[str, Any]] = []
    fraud_results: List[Dict[str, Any]] = []
    merchant_results: List[Dict[str, Any]] = []
    cashflow_results: Dict[str, Any] = {}
    insights: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"
