"""LangGraph state schema for FinFlow agent."""

from typing import Annotated, Any
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State container for agent execution."""

    messages: list
    transactions: list[dict]
    selected_tools: list[str]
    enriched_results: list[dict]
    anomaly_results: list[dict]
    fraud_results: list[dict]
    cashflow_results: dict
    merchant_results: list[dict]
    insights: dict
    agent_plan: str
    final_response: str
    grounding_score: float
    llm_grounding_score: float
    used_fallback: bool
    execution_trace: list[str]
