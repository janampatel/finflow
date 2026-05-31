"""FinFlow Streamlit Dashboard - Main Entry Point."""

import streamlit as st
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="FinFlow Dashboard",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .high-risk {
        background-color: #ffcccc;
    }
    .medium-risk {
        background-color: #fff3cd;
    }
    .low-risk {
        background-color: #d4edda;
    }
    .grounding-high {
        color: #28a745;
        font-weight: bold;
    }
    .grounding-low {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

if "page_state" not in st.session_state:
    st.session_state.page_state = {}

# Sidebar
with st.sidebar:
    st.title("⚙️ FinFlow Settings")

    st.session_state.api_url = st.text_input(
        "API Base URL",
        value=st.session_state.api_url,
        help="FastAPI endpoint URL"
    )

    st.divider()
    st.markdown("### 📊 Navigation")
    st.markdown("""
    1. **Transactions** — Explore and enrich transaction data
    2. **Anomalies** — View flagged suspicious transactions
    3. **Financial Health** — Personal financial wellness score
    4. **Agent Trace** — See exactly how AI processes transactions
    """)

    st.divider()
    st.info("💡 **Pro Tip**: Use the Agent Trace page to understand the AI decision-making process.")

# Main title
st.title("💳 FinFlow — Financial Transaction Intelligence")
st.markdown("""
**FinFlow** analyzes your financial transactions using AI to detect anomalies,
categorize spending, and provide actionable financial health insights.

Built on **LangGraph** agent orchestration + **FinBERT** transaction categorization +
deterministic financial tools (no AI-computed numbers).
""")

# Quick stats
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("System Status", "🟢 Healthy")
with col2:
    st.metric("API Version", "1.0.0")
with col3:
    st.metric("Model Type", "FinBERT")
with col4:
    st.metric("Min Grounding", "0.85")

st.divider()

st.markdown("### 🚀 Get Started")
st.markdown("""
**Step 1:** Navigate to the **Transactions** page to explore transaction data.
**Step 2:** Switch to **Agent Trace** to run a live enrichment pipeline.
**Step 3:** Check **Anomalies** to see detected fraud patterns.
**Step 4:** Review **Financial Health** for overall wellness score.
""")

st.divider()

# Architecture overview
with st.expander("🏗️ System Architecture"):
    st.markdown("""
    ```
    User Input → Planner (LLM decides which tools)
              ↓
         Tools Coordinator (parallel execution)
         ├── Enrichment Tool (FinBERT categorization)
         ├── Anomaly Tool (PyOD Isolation Forest)
         ├── Cashflow Tool (statsmodels trend analysis)
         └── Merchant Tool (rapidfuzz fuzzy matching)
              ↓
           Insight Tool (aggregate health score)
              ↓
         Synthesis (LLM narrative generation)
              ↓
          Validation (hallucination guard, grounding score ≥ 0.85)
              ↓
          Output → API Response → Dashboard Visualization
    ```

    **Determinism Guarantee:** Every financial computation happens in pure Python.
    The LLM only *plans* and *narrates*, never *computes*.
    """)

st.markdown("""
---
*FinFlow Dashboard v1.0 — Phases 0-5 Complete, Phase 6 Interactive Visualization*
""")
