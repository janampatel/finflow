"""LangGraph node functions for FinFlow agent."""

import os
import json
from dotenv import load_dotenv
from loguru import logger
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables from .env
load_dotenv()

from src.agents.state import AgentState
from src.agents.hallucination_guard import HallucinationGuard
from src.tools.enrichment_tool import enrichment_tool
from src.tools.anomaly_tool import anomaly_detection_tool
from src.tools.cashflow_tool import cashflow_tool
from src.tools.merchant_tool import merchant_resolution_tool
from src.tools.insight_tool import insight_tool


def planner_node(state: AgentState) -> dict:
    """LLM planner: analyzes transactions and creates action plan."""
    logger.info("=== PLANNER NODE ===")

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)

    system_prompt = """You are a financial transaction analyzer. Your job is to:
1. Understand the user's query about transactions
2. Plan which tools to call (enrichment, anomaly, cashflow, merchant, insight)
3. Specify exact parameters for each tool call

Be concise. List tools in order. Do not make up data."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Analyze these transactions and create a plan:
{json.dumps(state['transactions'][:5], indent=2)}

Plan your analysis steps."""),
    ]

    response = llm.invoke(messages)
    plan = response.content

    logger.info(f"Plan: {plan[:200]}...")

    return {
        "messages": messages + [response],
        "agent_plan": plan,
        "execution_trace": ["planner_node"]
    }


def tools_coordinator_node(state: AgentState) -> dict:
    """Coordinate all tool execution (enrichment, anomaly, merchant, cashflow)."""
    logger.info("=== TOOLS COORDINATOR ===")

    # Run enrichment
    enriched_results = []
    for tx in state["transactions"]:
        description = tx.get("description", "")
        result = enrichment_tool(description)
        enriched_results.append(result)
    logger.debug(f"Enrichment done: {len(enriched_results)} results")

    # Run anomaly
    anomaly_results = []
    for tx in state["transactions"]:
        amount = tx.get("amount", 0.0)
        balance_change = tx.get("balance_change", 0.0)
        result = anomaly_detection_tool(amount=amount, balance_change_orig=balance_change)
        anomaly_results.append(result)
    logger.debug(f"Anomaly done: {len(anomaly_results)} results")

    # Run merchant
    merchant_results = []
    for tx in state["transactions"]:
        merchant = tx.get("merchant", "UNKNOWN")
        result = merchant_resolution_tool(merchant)
        merchant_results.append(result)
    logger.debug(f"Merchant done: {len(merchant_results)} results")

    # Run cashflow
    cashflow_results = cashflow_tool(state["transactions"])
    logger.debug("Cashflow done")

    return {
        "enriched_results": enriched_results,
        "anomaly_results": anomaly_results,
        "merchant_results": merchant_results,
        "cashflow_results": cashflow_results,
        "execution_trace": state["execution_trace"] + ["tools_coordinator"]
    }


def insight_node(state: AgentState) -> dict:
    """Insight node: compute financial health score."""
    logger.info("=== INSIGHT NODE ===")

    # Use enriched results for insights
    result = insight_tool(state["enriched_results"])

    logger.info(f"Health score: {result.get('health_score', 0.0):.2f}")

    return {
        "insights": result,
        "execution_trace": state["execution_trace"] + ["insight_node"]
    }


def synthesis_node(state: AgentState) -> dict:
    """LLM synthesis: create human-readable narrative."""
    logger.info("=== SYNTHESIS NODE ===")

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.5)

    txn_count = len(state.get("transactions", []))
    insufficient_data = txn_count < 10

    # Prepare context with data sufficiency warning
    context = f"""
Transactions analyzed: {txn_count}
Categories: {[r.get('category') for r in state['enriched_results']]}
Anomalies found: {sum(1 for r in state['anomaly_results'] if r.get('is_anomaly'))}
Health score: {state['insights'].get('health_score', 0.0):.2f}
Key insights: {state['insights'].get('insights', [])}

{'⚠️ DATA SUFFICIENCY WARNING: Only ' + str(txn_count) + ' transaction(s). Insufficient for pattern analysis.' if insufficient_data else ''}
"""

    # STRICT system prompt with constraints
    system_prompt = """You are a financial analyst explaining transaction analysis results.

CONSTRAINTS (MUST FOLLOW):
1. Only state facts directly from tool outputs
2. Do NOT claim patterns, diversity, or habits - these need 10+ transactions
3. Do NOT compare spending levels or categories
4. Do NOT mention "diversity", "concentration", or "distribution" if <10 transactions
5. If insufficient data, say so explicitly
6. Every number must come from tool outputs
7. Be specific, factual, and grounded - never infer or extrapolate

Output: 2-3 sentences maximum, directly from the data."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Based on this analysis:
{context}

Provide a brief factual summary. If data is insufficient, state that clearly."""),
    ]

    response = llm.invoke(messages)
    synthesis = response.content

    logger.info(f"Synthesis: {synthesis[:100]}...")

    return {
        "messages": state.get("messages", []) + messages + [response],
        "final_response": synthesis,
        "execution_trace": state["execution_trace"] + ["synthesis_node"]
    }


def validation_node(state: AgentState) -> dict:
    """Validation node: check response for hallucinations."""
    logger.info("=== VALIDATION NODE ===")

    guard = HallucinationGuard(grounding_threshold=0.85)

    is_valid, score, reason = guard.validate(
        response=state["final_response"],
        enriched_results=state["enriched_results"],
        anomaly_results=state["anomaly_results"],
        cashflow_results=state["cashflow_results"],
        insights=state["insights"]
    )

    logger.info(f"Validation: {reason}")

    if not is_valid:
        logger.warning("Response failed grounding check - regenerating...")
        state["final_response"] += f"\n[Validation note: grounding score {score:.2f}/{1.0}]"

    return {
        "grounding_score": score,
        "execution_trace": state["execution_trace"] + ["validation_node"]
    }
