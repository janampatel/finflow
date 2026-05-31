"""Anomaly Feed - View detected suspicious transactions with severity filters."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="Anomalies", page_icon="🚨", layout="wide")

st.title("🚨 Anomaly Feed")
st.markdown("Suspicious transactions flagged by the anomaly detection system.")

# Initialize session state
if "anomalies_data" not in st.session_state:
    st.session_state.anomalies_data = None

if "anomaly_severity_filter" not in st.session_state:
    st.session_state.anomaly_severity_filter = "All"

# Sidebar
with st.sidebar:
    st.header("🔍 Filters")

    if st.button("📥 Load Sample Anomalies"):
        # Create synthetic anomaly data
        anomalies_list = [
            {
                "transaction_id": "TX000015",
                "timestamp": (datetime.now() - timedelta(days=5)).isoformat(),
                "description": "UNUSUAL TRANSFER 50000 USD",
                "amount": 50000.0,
                "category": "Transfer",
                "anomaly_score": 0.92,
                "severity": "high",
                "reason": "Amount 10x user average; occurs at unusual time",
                "merchant": "Unknown"
            },
            {
                "transaction_id": "TX000018",
                "timestamp": (datetime.now() - timedelta(days=3)).isoformat(),
                "description": "INTERNATIONAL CHARGE AUSTRALIA",
                "amount": 1250.0,
                "category": "Travel",
                "anomaly_score": 0.68,
                "severity": "medium",
                "reason": "International transaction; user location mismatch",
                "merchant": "Qantas Airlines"
            },
            {
                "transaction_id": "TX000012",
                "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
                "description": "MULTIPLE ATM WITHDRAWALS",
                "amount": 600.0,
                "category": "Transfer",
                "anomaly_score": 0.45,
                "severity": "low",
                "reason": "3 ATM withdrawals in 2 hours; pattern break",
                "merchant": "ATM Network"
            },
            {
                "transaction_id": "TX000025",
                "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
                "description": "CRYPTOCURRENCY EXCHANGE BUY",
                "amount": 5000.0,
                "category": "Investment",
                "anomaly_score": 0.71,
                "severity": "medium",
                "reason": "New merchant; high-risk category",
                "merchant": "CoinBase"
            },
        ]
        st.session_state.anomalies_data = pd.DataFrame(anomalies_list)
        st.success(f"✅ Loaded {len(anomalies_list)} sample anomalies")

    if st.session_state.anomalies_data is not None:
        # Severity filter
        st.session_state.anomaly_severity_filter = st.selectbox(
            "Severity Filter",
            ["All", "High", "Medium", "Low"],
            index=0
        )

        # Score range
        min_score = st.slider(
            "Min Anomaly Score",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05
        )

        st.divider()
        st.markdown("**Color Coding:**")
        st.markdown("- 🔴 **High (≥0.70)** — Fraud likely")
        st.markdown("- 🟡 **Medium (0.50-0.70)** — Monitor closely")
        st.markdown("- 🟢 **Low (<0.50)** — Unusual but benign")

# Main content
if st.session_state.anomalies_data is None:
    st.info("👈 Click **Load Sample Anomalies** in the sidebar to begin")

else:
    df = st.session_state.anomalies_data.copy()

    # Apply filters
    if st.session_state.anomaly_severity_filter != "All":
        df = df[df["severity"] == st.session_state.anomaly_severity_filter.lower()]

    df = df[df["anomaly_score"] >= 0.3]

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Flagged", len(df))
    with col2:
        high_count = len(df[df["severity"] == "high"])
        st.metric("High Severity", high_count, delta=f"{high_count} critical")
    with col3:
        total_anomaly_amount = df["amount"].sum()
        st.metric("Total Amount", f"${total_anomaly_amount:,.2f}")
    with col4:
        avg_score = df["anomaly_score"].mean()
        st.metric("Avg Anomaly Score", f"{avg_score:.2f}")

    st.divider()

    # Anomaly table
    st.subheader("Flagged Transactions")

    display_df = df[["transaction_id", "timestamp", "description", "merchant", "amount",
                     "anomaly_score", "severity"]].copy()
    display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}")
    display_df["score"] = display_df["anomaly_score"].apply(lambda x: f"{x:.2f}")
    display_df = display_df.drop("anomaly_score", axis=1)

    # Color-coded rows
    st.dataframe(
        display_df.rename(columns={"score": "Anomaly Score"}),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Anomaly Score Distribution")
        fig = px.histogram(
            df,
            x="anomaly_score",
            nbins=15,
            color="severity",
            color_discrete_map={"high": "#d32f2f", "medium": "#fbc02d", "low": "#388e3c"},
            title="Score Distribution by Severity"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Severity Breakdown")
        severity_counts = df["severity"].value_counts()
        fig = px.bar(
            x=severity_counts.index,
            y=severity_counts.values,
            color=severity_counts.index,
            color_discrete_map={"high": "#d32f2f", "medium": "#fbc02d", "low": "#388e3c"},
            labels={"x": "Severity", "y": "Count"},
            title="Flagged Transactions by Severity"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Anomalies Over Time")
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        timeline = df.groupby("date").size().reset_index(name="count")
        fig = px.area(
            timeline,
            x="date",
            y="count",
            title="Anomaly Frequency by Day",
            labels={"count": "Flagged Count"}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Category Breakdown")
        cat_counts = df["category"].value_counts().head(8)
        fig = px.pie(
            values=cat_counts.values,
            names=cat_counts.index,
            title="Anomalies by Category"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Detailed anomaly view
    st.subheader("📋 Detailed View")
    selected_idx = st.selectbox(
        "Select Anomaly",
        range(len(df)),
        format_func=lambda i: f"{df.iloc[i]['transaction_id']} — {df.iloc[i]['description']} ({df.iloc[i]['severity']})"
    )

    selected_anomaly = df.iloc[selected_idx].to_dict()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anomaly Score", f"{selected_anomaly['anomaly_score']:.3f}")
    with col2:
        severity = selected_anomaly["severity"].upper()
        if severity == "HIGH":
            st.metric("Severity", "🔴 " + severity)
        elif severity == "MEDIUM":
            st.metric("Severity", "🟡 " + severity)
        else:
            st.metric("Severity", "🟢 " + severity)
    with col3:
        st.metric("Amount", f"${selected_anomaly['amount']:,.2f}")

    st.markdown(f"**Reason:** {selected_anomaly['reason']}")

    st.info(f"""
    **Recommendation:**
    - Verify transaction legitimacy before proceeding
    - Contact cardholder if anomaly score > 0.85
    - Flag to fraud team if score > 0.90
    """)
