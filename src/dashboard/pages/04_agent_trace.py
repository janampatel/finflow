"""Agent Trace - Real-time execution with user transaction history from database."""

import streamlit as st
import requests
import json
from typing import Optional
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Agent Trace", page_icon="🔬", layout="wide")

st.title("🔬 Agent Execution Trace")
st.markdown("""
This page runs the agent with **real transaction history from the database**.

Flow:
1. Enter user ID to load their transaction history (last 30 transactions)
2. Add a new transaction to analyze
3. Agent runs on complete dataset (history + new)
4. Get meaningful insights based on actual patterns
""")

# Initialize session state
if "last_trace" not in st.session_state:
    st.session_state.last_trace = None
if "user_history" not in st.session_state:
    st.session_state.user_history = None
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.api_url = st.text_input(
        "API Base URL",
        value=st.session_state.api_url
    )

# Step 1: Load User History
st.subheader("📊 Step 1: Load User Transaction History")

col1, col2 = st.columns(2)

with col1:
    user_id = st.text_input(
        "User ID",
        value="C1000000007",
        help="Enter a user ID to load their transaction history"
    )

with col2:
    if st.button("📥 Load User History", key="load_history"):
        with st.spinner(f"Loading transaction history for {user_id}..."):
            try:
                # Try to get user's transactions from API
                response = requests.get(
                    f"{st.session_state.api_url}/api/transactions",
                    params={"user_id": user_id, "limit": 100, "offset": 0},
                    timeout=10
                )
                response.raise_for_status()
                result = response.json()

                txs = result.get("data", [])
                total = result.get("pagination", {}).get("total", 0)

                if txs:
                    st.session_state.user_history = txs[:30]  # Use only last 30
                    st.success(f"✅ Loaded {len(txs[:30])} transactions (Total for user: {total})")

                    if total == 0:
                        st.warning(f"⚠️ Only {len(txs)} transactions found for this user")
                else:
                    st.warning(f"No transactions found for user {user_id}")
                    st.info("""
                    Try fetching a random user:
                    ```bash
                    curl "http://localhost:8000/api/transactions?limit=1"
                    ```
                    This will show an available user ID.
                    """)

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API. Make sure FastAPI is running.")
            except Exception as e:
                st.error(f"Error loading history: {e}")

# Display user history if loaded
if st.session_state.user_history:
    history_df = pd.DataFrame(st.session_state.user_history)

    st.info(f"""
    ✅ **User History Loaded:** {len(st.session_state.user_history)} transactions

    This history will be used with the new transaction for meaningful insights.
    """)

    with st.expander("📋 View Transaction History"):
        display_cols = ["type", "amount", "nameOrig", "nameDest"]
        available = [c for c in display_cols if c in history_df.columns]
        st.dataframe(history_df[available].head(10), use_container_width=True, hide_index=True)

st.divider()

# Step 2: Add New Transaction
st.subheader("🆕 Step 2: Enter New Transaction to Analyze")

col1, col2, col3 = st.columns(3)

with col1:
    tx_description = st.text_input(
        "Transaction Description",
        value="AMZN MKTPLC",
        help="Raw transaction string (e.g., STARBUCKS, WALMART, UBER)"
    )

with col2:
    tx_amount = st.number_input(
        "Amount",
        min_value=0.01,
        value=100.00,
        step=0.01
    )

with col3:
    tx_type = st.selectbox(
        "Type",
        ["DEBIT", "CASH_OUT", "PAYMENT", "TRANSFER", "CASH_IN"],
        index=0
    )

st.divider()

# Step 3: Run Agent
st.subheader("🚀 Step 3: Run Agent Pipeline")

if not st.session_state.user_history:
    st.warning("⚠️ Load user history first to get meaningful insights!")
    st.info("""
    Without user history:
    - No patterns to analyze
    - Can't assess spending diversity
    - No baseline for anomaly detection

    With user history:
    - Full spending patterns visible
    - Anomalies detected relative to user's typical behavior
    - Meaningful health assessment
    """)

else:
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Run Agent Pipeline", key="run_agent"):
            with st.spinner("⏳ Processing transaction through agent pipeline with user history..."):
                try:
                    # Map database transactions to API schema
                    def map_transaction(db_tx):
                        """Convert database transaction to API schema."""
                        return {
                            "description": db_tx.get("description") or f"{db_tx.get('type', 'UNKNOWN')} - {db_tx.get('nameDest', 'Unknown')}",
                            "amount": float(db_tx.get("amount", 0.0)),
                            "balance_change": float(db_tx.get("newbalanceOrig", 0.0) - db_tx.get("oldbalanceOrg", 0.0)),
                            "merchant": db_tx.get("nameDest") or db_tx.get("nameOrig") or "Unknown"
                        }

                    # Convert user history to API schema
                    all_transactions = [map_transaction(tx) for tx in st.session_state.user_history]

                    # Add new transaction
                    new_tx = {
                        "description": tx_description,
                        "amount": tx_amount,
                        "balance_change": -tx_amount if tx_type in ["CASH_OUT", "DEBIT", "PAYMENT"] else tx_amount,
                        "merchant": tx_description.split()[0] if tx_description else "Unknown"
                    }
                    all_transactions.append(new_tx)

                    payload = {"transactions": all_transactions}

                    st.info(f"📊 Sending {len(all_transactions)} transactions to agent (30 history + 1 new)")

                    # Call API
                    response = requests.post(
                        f"{st.session_state.api_url}/api/analyze",
                        json=payload,
                        timeout=30
                    )

                    if response.status_code == 422:
                        st.error("❌ Schema Error: Transaction format invalid")
                        st.error(response.json().get("detail", "Unknown validation error"))
                    else:
                        response.raise_for_status()
                        result = response.json()

                        # Store trace
                        st.session_state.last_trace = result
                        st.success("✅ Agent pipeline completed successfully")

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to FastAPI backend")
                    st.info("Make sure FastAPI is running: `python -m uvicorn src.api.main:app --reload`")
                except Exception as e:
                    st.error(f"❌ Pipeline failed: {e}")
                    st.info("Try loading demo trace to verify setup is correct")

    with col2:
        if st.button("📥 Load Demo Trace", key="load_sample"):
            demo_trace = {
                "final_response": "User frequently shops on Amazon (25% of transactions). New $100 purchase is within normal range. Health score 72.5 indicates moderate financial wellness. No anomalies detected.",
                "grounding_score": 0.94,
                "execution_trace": ["planner", "tools_coordinator", "insight", "synthesis", "validation"],
                "enriched_results": [
                    {
                        "category": "Shopping",
                        "confidence": 0.96,
                        "is_low_confidence": False,
                        "raw_description": "AMZN MKTPLC",
                        "tool": "enrichment_tool"
                    }
                ],
                "anomaly_results": [
                    {
                        "is_anomaly": False,
                        "anomaly_score": 0.22,
                        "anomaly_reason": "Amount within normal range for user",
                        "severity": "low",
                        "tool": "anomaly_tool"
                    }
                ],
                "merchant_results": [
                    {
                        "normalized_merchant": "AMAZON",
                        "match_score": 1.0,
                        "inferred_category": "Shopping",
                        "tool": "merchant_tool"
                    }
                ],
                "cashflow_results": {
                    "net_cash_flow": -100.00,
                    "tool": "cashflow_tool"
                },
                "insights": {
                    "health_score": 72.5,
                    "risk_level": "low",
                    "tool": "insight_tool"
                }
            }
            st.session_state.last_trace = demo_trace
            st.success("✅ Demo trace loaded")

st.divider()

# Display Results
if st.session_state.last_trace:
    trace = st.session_state.last_trace

    # Execution Summary
    st.subheader("⏱️ Execution Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        txn_count = len(st.session_state.user_history or []) + 1
        st.metric("Transactions Analyzed", txn_count)
    with col2:
        st.metric("Execution Nodes", len(trace.get("execution_trace", [])))
    with col3:
        grounding = trace.get("grounding_score", 0.0)
        st.metric("Grounding Score", f"{grounding:.3f}")
    with col4:
        if grounding >= 0.85:
            st.metric("Status", "✅ Passed")
        else:
            st.metric("Status", "⚠️ Low")

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Planner",
        "🔧 Tools",
        "💡 Synthesis",
        "🛡️ Validation",
        "📥 Download"
    ])

    with tab1:
        st.markdown("""
        **Role:** Decides which tools to invoke based on transaction + user history

        **Constraint:** LLM must only PLAN, never COMPUTE numbers.
        """)

        st.info("""
        **Planner Decision:**
        ✅ enrichment_tool — categorize with FinBERT
        ✅ anomaly_tool — detect fraud (vs user's baseline)
        ✅ merchant_tool — resolve merchant name
        ✅ cashflow_tool — compute impact on user's cash flow
        ✅ insight_tool — aggregate health score

        **Context Used:** User's last 30 transactions + new transaction
        """)

    with tab2:
        st.markdown("""
        **Role:** Execute all tools using user history as baseline

        **Property:** Tools are deterministic (same input → same output)
        """)

        # Enrichment
        st.markdown("### Enrichment Tool (FinBERT)")
        enrichment = trace.get("enriched_results", [{}])[-1] if trace.get("enriched_results") else {}

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Category", enrichment.get("category", "Unknown"))
        with col2:
            st.metric("Confidence", f"{enrichment.get('confidence', 0.0):.1%}")
        with col3:
            status = "Low ⚠️" if enrichment.get("is_low_confidence") else "High ✅"
            st.metric("Level", status)

        # Anomaly
        st.markdown("### Anomaly Tool (PyOD - User Baseline)")
        anomaly = trace.get("anomaly_results", [{}])[-1] if trace.get("anomaly_results") else {}

        col1, col2, col3 = st.columns(3)
        with col1:
            is_anom = "🚨 Yes" if anomaly.get("is_anomaly") else "✅ No"
            st.metric("Anomaly", is_anom)
        with col2:
            st.metric("Score", f"{anomaly.get('anomaly_score', 0.0):.2f}")
        with col3:
            severity = anomaly.get("severity", "low").upper()
            color = "🔴 HIGH" if severity == "HIGH" else "🟡 MEDIUM" if severity == "MEDIUM" else "🟢 LOW"
            st.metric("Severity", color)

        st.markdown(f"*Reason:* {anomaly.get('anomaly_reason', 'N/A')}")

        # Merchant
        st.markdown("### Merchant Tool (RapidFuzz)")
        merchant = trace.get("merchant_results", [{}])[-1] if trace.get("merchant_results") else {}

        merchant_name = merchant.get("normalized_merchant") or "Unknown"
        match_score = merchant.get("match_score", 0.0)
        if isinstance(match_score, float) and match_score <= 1:
            match_score = match_score * 100

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Name", merchant_name)
        with col2:
            st.metric("Match", f"{match_score:.0f}%")
        with col3:
            category = merchant.get("inferred_category", "Unknown")
            st.metric("Category", category)

        # Insight
        st.markdown("### Insight Tool (Health Score)")
        insights = trace.get("insights", {})

        col1, col2 = st.columns(2)
        with col1:
            health_score = insights.get("health_score", 0.0)
            st.metric("Health Score", f"{health_score:.1f}")
        with col2:
            risk = insights.get("risk_level", "unknown")
            st.metric("Risk Level", risk.capitalize())

        st.markdown(f"*Based on user's {txn_count} transactions*")

    with tab3:
        st.markdown("""
        **Role:** Generate narrative using user history + tool outputs

        **Constraint:** Use ONLY facts from tools + user patterns
        """)

        st.info("**AI-Generated Narrative:**")
        st.write(f'"{trace.get("final_response", "")}"')

    with tab4:
        st.markdown("""
        **Role:** Validate claims are grounded in tool outputs

        **Score = Claims Traceable to Tools**
        - ≥0.85: Fully grounded ✅
        - <0.85: Contains unverified claims ❌
        """)

        grounding = trace.get("grounding_score", 0.0)
        passed = grounding >= 0.85

        if passed:
            st.success(f"✅ GROUNDING CHECK PASSED — Score: {grounding:.3f}")
        else:
            st.warning(f"⚠️ GROUNDING CHECK LOW — Score: {grounding:.3f}")

        st.progress(min(grounding, 1.0))

    with tab5:
        st.markdown("### Full Execution State")
        st.json(trace)

        st.divider()

        st.markdown("### Download Trace")
        st.download_button(
            label="📥 Download as JSON",
            data=json.dumps(trace, indent=2),
            file_name=f"agent_trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

else:
    st.info("""
    👈 **Run the agent pipeline** to see execution trace.

    Or click **Load Demo Trace** to see example output.
    """)

st.divider()

st.markdown("""
---
### 🎯 How This Works

**With Real User History:**
- ✅ Meaningful pattern analysis (user shops Amazon 25%, normal)
- ✅ Smart anomaly detection (unusual for THIS user)
- ✅ Accurate health assessment (based on actual spending)
- ✅ High grounding score (0.90+) — claims backed by data

**Without User History:**
- ❌ Can't assess patterns (1 txn = no patterns)
- ❌ Anomaly detection meaningless (no baseline)
- ❌ Health score not interpretable
- ❌ Low grounding score (claims can't be verified)
""")
