"""LangGraph node functions for FinFlow agent."""

import os
import re
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
from src.tools.fraud_tool import fraud_detection_tool
from src.tools.cashflow_tool import cashflow_tool
from src.tools.merchant_tool import merchant_resolution_tool
from src.tools.insight_tool import insight_tool


# Tools the planner may route to. Enrichment (categorization) and fraud
# (supervised fraud scoring) are the always-on spine; anomaly/merchant/cashflow
# are optional and chosen by the planner.
VALID_TOOLS = ["enrichment", "anomaly", "fraud", "merchant", "cashflow"]


def _parse_plan(raw: str) -> tuple[list[str], str]:
    """Parse the planner's JSON tool-selection, with robust fallbacks."""
    selected: list[str] = []
    reasoning = ""

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            selected = [t for t in obj.get("tools_to_run", []) if t in VALID_TOOLS]
            reasoning = str(obj.get("reasoning", ""))[:300]
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: keyword scan, then default to all tools
    if not selected:
        selected = [t for t in VALID_TOOLS if t in raw.lower()] or list(VALID_TOOLS)

    # Guarantee the spine tools run on every transaction: categorization
    # (enrichment) and fraud scoring are core safety checks a fintech always
    # performs; the planner only decides the deeper optional analyses.
    for spine in ("fraud", "enrichment"):
        if spine not in selected:
            selected = [spine, *selected]

    return selected, reasoning or "Selected tools for analysis."


def planner_node(state: AgentState) -> dict:
    """LLM router: picks which deterministic tools to run for these transactions.

    Emits a compact JSON decision (fast, low-token) that actually gates which
    tools execute downstream — the planner call now has real routing purpose.
    """
    logger.info("=== PLANNER NODE ===")

    # Low temperature + small token budget → fast, deterministic routing.
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0, max_tokens=150)

    n = len(state["transactions"])
    sample = state["transactions"][:3]

    system_prompt = (
        "You are a routing planner for a financial analysis agent. Choose which "
        "deterministic tools to run for the given transactions.\n"
        "Valid tools: enrichment (categorize), anomaly (unsupervised novelty), "
        "fraud (supervised fraud probability), merchant (resolve merchant name), "
        "cashflow (income/expense summary).\n"
        "Respond with ONLY compact JSON, no prose:\n"
        '{"tools_to_run": ["enrichment", "anomaly", "merchant", "cashflow"], '
        '"reasoning": "<one short sentence>"}\n'
        "Always include enrichment. Never compute or invent numbers."
    )
    human = f"{n} transaction(s). Sample: {json.dumps(sample)}"

    try:
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human)]
        )
        selected, reasoning = _parse_plan(response.content)
    except Exception as e:  # network/LLM failure → safe default
        logger.warning(f"Planner failed ({e}); defaulting to all tools")
        selected, reasoning = list(VALID_TOOLS), "Default plan: run all tools."

    logger.info(f"Planner routed to: {selected}")

    return {
        "agent_plan": reasoning,
        "selected_tools": selected,
        "execution_trace": ["planner_node"],
    }


def tools_coordinator_node(state: AgentState) -> dict:
    """Run only the tools the planner selected. Skipped tools yield empty results."""
    logger.info("=== TOOLS COORDINATOR ===")

    selected = state.get("selected_tools") or list(VALID_TOOLS)
    txs = state["transactions"]

    enriched_results = []
    if "enrichment" in selected:
        enriched_results = [enrichment_tool(tx.get("description", "")) for tx in txs]
    logger.debug(f"Enrichment: {len(enriched_results)} results (selected={'enrichment' in selected})")

    anomaly_results = []
    if "anomaly" in selected:
        anomaly_results = [
            anomaly_detection_tool(
                amount=tx.get("amount", 0.0),
                balance_change_orig=tx.get("balance_change", 0.0),
                balance_change_dest=tx.get("balance_change_dest", 0.0),
            )
            for tx in txs
        ]
    logger.debug(f"Anomaly: {len(anomaly_results)} results (selected={'anomaly' in selected})")

    fraud_results = []
    if "fraud" in selected:
        fraud_results = [
            fraud_detection_tool(
                amount=tx.get("amount", 0.0),
                balance_change_orig=tx.get("balance_change", 0.0),
                balance_change_dest=tx.get("balance_change_dest", 0.0),
                tx_type=tx.get("transaction_type", ""),
            )
            for tx in txs
        ]
    logger.debug(f"Fraud: {len(fraud_results)} results (selected={'fraud' in selected})")

    merchant_results = []
    if "merchant" in selected:
        merchant_results = [merchant_resolution_tool(tx.get("merchant", "UNKNOWN")) for tx in txs]
    logger.debug(f"Merchant: {len(merchant_results)} results (selected={'merchant' in selected})")

    cashflow_results = {}
    if "cashflow" in selected:
        cashflow_results = cashflow_tool(txs)
    logger.debug(f"Cashflow: selected={'cashflow' in selected}")

    return {
        "enriched_results": enriched_results,
        "anomaly_results": anomaly_results,
        "fraud_results": fraud_results,
        "merchant_results": merchant_results,
        "cashflow_results": cashflow_results,
        "execution_trace": state["execution_trace"] + ["tools_coordinator"],
    }


def insight_node(state: AgentState) -> dict:
    """Insight node: compute financial health score."""
    logger.info("=== INSIGHT NODE ===")

    enriched = state.get("enriched_results", [])

    # Safety: if the planner routed away from enrichment, skip scoring gracefully.
    if not enriched:
        logger.debug("No enriched results — emitting default insights")
        result = {
            "health_score": 0.0,
            "components": {},
            "metrics": {"num_transactions": len(state.get("transactions", []))},
            "insights": [],
            "tool": "insight_tool",
        }
    else:
        result = insight_tool(enriched)

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

    fraud_results = state.get("fraud_results", [])
    fraud_flagged = sum(1 for r in fraud_results if r.get("is_fraud_predicted"))
    max_fraud_prob = max((r.get("fraud_probability", 0.0) for r in fraud_results), default=0.0)

    # Prepare context with data sufficiency warning
    context = f"""
Transactions analyzed: {txn_count}
Categories: {[r.get('category') for r in state['enriched_results']]}
Anomalies found: {sum(1 for r in state['anomaly_results'] if r.get('is_anomaly'))}
Fraud flagged: {fraud_flagged} (max fraud probability: {max_fraud_prob:.2f})
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


def _deterministic_summary(
    enriched: list[dict], anomaly: list[dict], insights: dict, fraud: list[dict] | None = None
) -> str:
    """Build a narrative from tool numbers only — grounded by construction.

    Used as a fallback when the LLM narrative fails the grounding check, so the
    system never serves ungrounded output (the deterministic core of the design).
    """
    n = len(enriched)
    cats: dict[str, int] = {}
    for r in enriched:
        c = r.get("category")
        if c:
            cats[c] = cats.get(c, 0) + 1

    parts = [f"{n} transaction{'s' if n != 1 else ''} were analyzed across {len(cats)} categor{'ies' if len(cats) != 1 else 'y'}."]
    if cats:
        top = max(cats, key=cats.get)
        parts.append(f"The most frequent category is {top}.")
    if anomaly:
        n_anom = sum(1 for a in anomaly if a.get("is_anomaly"))
        parts.append(f"{n_anom} anomal{'ies were' if n_anom != 1 else 'y was'} detected." if n_anom else "No anomalies were detected.")
    if fraud:
        n_fraud = sum(1 for f in fraud if f.get("is_fraud_predicted"))
        parts.append(f"{n_fraud} transaction{'s were' if n_fraud != 1 else ' was'} flagged as likely fraud." if n_fraud else "No transactions were flagged as fraud.")
    health = insights.get("health_score")
    if isinstance(health, (int, float)):
        parts.append(f"The financial health score is {health:.2f}.")
    if n < 10:
        parts.append("Data is limited; pattern-level conclusions are not drawn.")
    return " ".join(parts)


def validation_node(state: AgentState) -> dict:
    """Validate the narrative; fall back to a deterministic grounded summary if it fails."""
    logger.info("=== VALIDATION NODE ===")

    guard = HallucinationGuard(grounding_threshold=0.85)
    final = state["final_response"]

    fraud_results = state.get("fraud_results", [])

    is_valid, score, reason = guard.validate(
        response=final,
        enriched_results=state["enriched_results"],
        anomaly_results=state["anomaly_results"],
        cashflow_results=state["cashflow_results"],
        insights=state["insights"],
        fraud_results=fraud_results,
    )
    logger.info(f"Validation: {reason} (LLM grounding={score:.2f})")

    llm_grounding = score
    used_fallback = False

    if not is_valid:
        # Remediate: serve a summary built only from tool outputs.
        final = _deterministic_summary(
            state["enriched_results"], state["anomaly_results"], state["insights"], fraud_results
        )
        _, score, _ = guard.validate(
            response=final,
            enriched_results=state["enriched_results"],
            anomaly_results=state["anomaly_results"],
            cashflow_results=state["cashflow_results"],
            insights=state["insights"],
            fraud_results=fraud_results,
        )
        used_fallback = True
        logger.warning(
            f"LLM narrative ungrounded ({llm_grounding:.2f}); served deterministic summary "
            f"(grounding={score:.2f})"
        )

    return {
        "final_response": final,
        "grounding_score": score,
        "llm_grounding_score": llm_grounding,
        "used_fallback": used_fallback,
        "execution_trace": state["execution_trace"] + ["validation_node"],
    }
