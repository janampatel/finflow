"""Pydantic schemas for API requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class Transaction(BaseModel):
    """Single transaction input."""

    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., description="Transaction amount")
    balance_change: float = Field(..., description="Balance change")
    merchant: str = Field(..., description="Merchant name")


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

    final_response: str = Field(..., description="Agent's narrative response")
    grounding_score: float = Field(..., ge=0.0, le=1.0, description="Hallucination guard score")
    execution_trace: List[str] = Field(..., description="Execution nodes in order")

    enriched_results: List[Dict[str, Any]] = []
    anomaly_results: List[Dict[str, Any]] = []
    merchant_results: List[Dict[str, Any]] = []
    cashflow_results: Dict[str, Any] = {}
    insights: Dict[str, Any] = {}


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"
