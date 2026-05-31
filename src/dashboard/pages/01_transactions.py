"""Transaction Explorer - Browse real transactions with pagination and filtering."""

import streamlit as st
import requests
import pandas as pd
from typing import Optional
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Transactions", page_icon="📝", layout="wide")

st.title("📝 Transaction Explorer")
st.markdown("Browse all transactions with real-time enrichment and live categorization.")

# Initialize session state
if "tx_page" not in st.session_state:
    st.session_state.tx_page = 0
if "tx_per_page" not in st.session_state:
    st.session_state.tx_per_page = 50
if "tx_data" not in st.session_state:
    st.session_state.tx_data = None
if "tx_total_count" not in st.session_state:
    st.session_state.tx_total_count = 0
if "enrichment_cache" not in st.session_state:
    st.session_state.enrichment_cache = {}
if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters & Settings")

    # API URL
    st.session_state.api_url = st.text_input(
        "API Base URL",
        value=st.session_state.api_url,
        help="FastAPI endpoint"
    )

    st.divider()

    # Load data
    if st.button("📥 Load Transactions from API"):
        with st.spinner("Fetching transaction data from database..."):
            try:
                response = requests.get(
                    f"{st.session_state.api_url}/api/transactions",
                    params={"limit": 1000, "offset": 0},
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()

                st.session_state.tx_data = result["data"]
                st.session_state.tx_total_count = result["pagination"]["total"]
                st.session_state.tx_page = 0

                st.success(f"✅ Loaded {len(result['data'])} transactions (Total: {result['pagination']['total']})")

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API. Ensure FastAPI is running: `python -m uvicorn src.api.main:app --reload`")
            except Exception as e:
                st.error(f"Error fetching transactions: {e}")

    if st.session_state.tx_data is not None:
        st.divider()

        # User filter
        user_id = st.text_input(
            "Filter by User ID",
            help="Leave blank for all users"
        )

        # Transaction type filter
        tx_type = st.selectbox(
            "Transaction Type",
            ["All", "CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"],
            index=0
        )

        # Rows per page
        st.session_state.tx_per_page = st.selectbox(
            "Rows Per Page",
            [10, 25, 50, 100],
            index=2
        )

        # Statistics
        st.divider()
        st.markdown("### 📊 Current View Stats")
        st.metric("Total Transactions", f"{st.session_state.tx_total_count:,}")

# Main content
if st.session_state.tx_data is None:
    st.info("👈 Click **Load Transactions from API** in the sidebar to fetch real data from database")

else:
    df = pd.DataFrame(st.session_state.tx_data)

    if df.empty:
        st.warning("No transactions loaded yet.")
    else:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Transactions", len(df))
        with col2:
            debit_amount = df[df["type"].isin(["CASH_OUT", "DEBIT", "PAYMENT"])]["amount"].sum()
            st.metric("Total Debits", f"${debit_amount:,.2f}")
        with col3:
            credit_amount = df[df["type"].isin(["CASH_IN"])]["amount"].sum()
            st.metric("Total Credits", f"${credit_amount:,.2f}")
        with col4:
            net = credit_amount - debit_amount
            st.metric("Net Flow", f"${net:,.2f}")

        st.divider()

        # Pagination
        total_pages = (len(df) + st.session_state.tx_per_page - 1) // st.session_state.tx_per_page

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            if st.button("⬅️ Previous"):
                st.session_state.tx_page = max(0, st.session_state.tx_page - 1)
        with col2:
            st.session_state.tx_page = st.number_input(
                "Page",
                min_value=0,
                max_value=max(0, total_pages - 1),
                value=st.session_state.tx_page
            )
        with col3:
            if st.button("Next ➡️"):
                st.session_state.tx_page = min(total_pages - 1, st.session_state.tx_page + 1)
        with col4:
            st.write(f"Page {st.session_state.tx_page + 1} of {total_pages}")
        with col5:
            st.write("")

        # Display transaction table
        start_idx = st.session_state.tx_page * st.session_state.tx_per_page
        end_idx = start_idx + st.session_state.tx_per_page
        page_df = df.iloc[start_idx:end_idx]

        st.subheader(f"Transactions (Page {st.session_state.tx_page + 1})")

        # Create display columns
        display_cols = ["type", "amount", "nameOrig", "nameDest", "isFraud"]
        available_cols = [col for col in display_cols if col in page_df.columns]
        display_df = page_df[available_cols].copy()

        # Format columns
        if "amount" in display_df.columns:
            display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}")
        if "isFraud" in display_df.columns:
            display_df["is_fraud"] = display_df["isFraud"].apply(lambda x: "🚨 Yes" if x == 1 else "✅ No")
            display_df = display_df.drop("isFraud", axis=1)

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.divider()

        # Analysis charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Transaction Type Distribution")
            type_counts = df["type"].value_counts()
            fig = px.pie(
                values=type_counts.values,
                names=type_counts.index,
                title="Distribution by Type"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Amount Distribution")
            fig = px.histogram(
                df,
                x="amount",
                nbins=50,
                title="Transaction Amount Distribution",
                labels={"amount": "Amount ($)"}
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Fraud analysis
        st.subheader("🚨 Fraud Analysis")

        fraud_count = df[df["isFraud"] == 1].shape[0]
        fraud_rate = (fraud_count / len(df) * 100) if len(df) > 0 else 0.0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fraudulent Transactions", fraud_count)
        with col2:
            st.metric("Fraud Rate", f"{fraud_rate:.2f}%")
        with col3:
            avg_fraud_amount = df[df["isFraud"] == 1]["amount"].mean() if fraud_count > 0 else 0
            st.metric("Avg Fraud Amount", f"${avg_fraud_amount:,.2f}")

        # Fraud vs Normal comparison
        fraud_vs_normal = df.groupby("isFraud")["amount"].mean().reset_index()
        fraud_vs_normal["type"] = fraud_vs_normal["isFraud"].apply(lambda x: "Fraudulent" if x == 1 else "Normal")

        fig = px.bar(
            fraud_vs_normal,
            x="type",
            y="amount",
            color="type",
            color_discrete_map={0: "#388e3c", 1: "#d32f2f"},
            title="Average Amount: Fraudulent vs Normal"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Live enrichment section
        st.subheader("🚀 Live Enrichment")
        st.markdown("Select a transaction to enrich it with the agent pipeline:")

        if len(page_df) > 0:
            selected_tx_idx = st.selectbox(
                "Select Transaction",
                range(len(page_df)),
                format_func=lambda i: f"{page_df.iloc[i]['type']} — ${page_df.iloc[i]['amount']:,.2f}"
            )

            if st.button("🔬 Enrich Selected Transaction"):
                selected_tx = page_df.iloc[selected_tx_idx].to_dict()
                tx_id = str(selected_tx.get("step", "unknown"))

                # Check cache
                if tx_id not in st.session_state.enrichment_cache:
                    with st.spinner("Running enrichment pipeline..."):
                        try:
                            # Prepare transaction for API
                            tx_for_api = {
                                "description": f"{selected_tx['type']} TXN",
                                "amount": float(selected_tx["amount"]),
                                "balance_change": float(selected_tx.get("newbalanceOrig", selected_tx["amount"])),
                                "merchant": selected_tx.get("nameDest", "Unknown")
                            }

                            response = requests.post(
                                f"{st.session_state.api_url}/api/analyze",
                                json={"transactions": [tx_for_api]},
                                timeout=30
                            )
                            response.raise_for_status()
                            result = response.json()
                            st.session_state.enrichment_cache[tx_id] = result
                        except Exception as e:
                            st.error(f"Enrichment failed: {e}")
                            result = None
                else:
                    result = st.session_state.enrichment_cache[tx_id]

                if result:
                    st.success("✅ Enrichment complete")

                    # Display results
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Grounding Score", f"{result.get('grounding_score', 0.0):.3f}")
                    with col2:
                        grounding = result.get('grounding_score', 0.0)
                        status = "✅ Grounded" if grounding >= 0.85 else "⚠️ Low"
                        st.metric("Status", status)
                    with col3:
                        tools_count = len(result.get('execution_trace', []))
                        st.metric("Tools Called", tools_count)

                    # Full results expander
                    with st.expander("📋 Full Enrichment Results"):
                        st.json(result)
