"""Financial Health Dashboard - Overall wellness score and trends."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="Health", page_icon="❤️", layout="wide")

st.title("❤️ Financial Health Dashboard")
st.markdown("Your overall financial wellness score and key indicators.")

# Initialize session state
if "health_data" not in st.session_state:
    st.session_state.health_data = None

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    if st.button("📥 Load Sample Health Data"):

        st.session_state.health_data = {
            "health_score": 72.5,
            "risk_level": "medium",
            "score_components": {
                "cash_flow_score": 28.5,  # out of 40
                "stability_score": 22.3,   # out of 30
                "anomaly_score": 21.7      # out of 30
            },
            "net_cash_flow": 1250.00,
            "income_stability": 0.82,
            "debt_to_income_ratio": 0.35,
            "avg_monthly_spend": 3200.00,
            "top_spend_category": "Shopping",
            "monthly_income": 5000.00,
            "recurring_obligations": [
                {"name": "Rent", "amount": 1500.00, "frequency": "monthly"},
                {"name": "Gym", "amount": 49.99, "frequency": "monthly"},
                {"name": "Netflix", "amount": 15.99, "frequency": "monthly"},
            ],
            "cash_flow_trend": "improving",
            "top_insights": [
                "Your spending decreased by 12% compared to last month",
                "Income shows stable monthly pattern — good for planning",
                "No anomalies detected in the last 7 days"
            ]
        }
        st.success("✅ Loaded sample health data")

    # Time period selector
    time_period = st.selectbox(
        "Time Period",
        ["Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year"],
        index=0
    )

# Main content
if st.session_state.health_data is None:
    st.info("👈 Click **Load Sample Health Data** in the sidebar to begin")

else:
    health = st.session_state.health_data

    # Large health score gauge
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        # Create gauge chart
        score = health["health_score"]
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=score,
            title={"text": "Financial Health Score"},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 40], "color": "#ffcccc"},
                    {"range": [40, 70], "color": "#fff3cd"},
                    {"range": [70, 100], "color": "#d4edda"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 85
                }
            }
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.metric("Risk Level", health["risk_level"].capitalize())
        st.metric("Trend", "📈 " + health["cash_flow_trend"].capitalize())

    with col3:
        st.metric("Stability", f"{health['income_stability']:.1%}")
        st.metric("D/I Ratio", f"{health['debt_to_income_ratio']:.2f}")

    st.divider()

    # Score components breakdown
    st.subheader("📊 Score Components")

    col1, col2, col3 = st.columns(3)

    components = health["score_components"]

    with col1:
        # Cash flow (out of 40)
        cf_score = components["cash_flow_score"]
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=cf_score,
            gauge={"axis": {"range": [0, 40]}},
            title={"text": "Cash Flow (40 pts)"}
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Stability (out of 30)
        stab_score = components["stability_score"]
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=stab_score,
            gauge={"axis": {"range": [0, 30]}},
            title={"text": "Stability (30 pts)"}
        ))
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        # Anomaly (out of 30)
        anom_score = components["anomaly_score"]
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=anom_score,
            gauge={"axis": {"range": [0, 30]}},
            title={"text": "Anomaly (30 pts)"}
        ))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Cash flow section
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💰 Cash Flow Summary")

        st.metric(
            "Monthly Income",
            f"${health['monthly_income']:,.2f}",
            delta="Stable"
        )
        st.metric(
            "Monthly Spend",
            f"${health['avg_monthly_spend']:,.2f}",
            delta="-12% (Improving)"
        )
        st.metric(
            "Net Cash Flow (30-day)",
            f"${health['net_cash_flow']:,.2f}",
            delta="✅ Positive"
        )

    with col2:
        st.subheader("📈 30-Day Cash Flow Trend")

        # Generate mock daily cashflow
        dates = [(datetime.now() - timedelta(days=29-i)).date() for i in range(30)]
        daily_cf = np.cumsum(np.random.normal(loc=40, scale=60, size=30))

        cf_df = pd.DataFrame({
            "date": dates,
            "cumulative_cf": daily_cf
        })

        fig = px.line(
            cf_df,
            x="date",
            y="cumulative_cf",
            title="Cumulative Cash Flow Trend",
            labels={"cumulative_cf": "Cumulative ($)"}
        )
        fig.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Spending analysis
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🛍️ Spending Categories")
        categories = {
            "Food & Dining": 450,
            "Shopping": 680,
            "Entertainment": 320,
            "Utilities": 180,
            "Travel": 570,
            "Other": 400
        }
        fig = px.donut(
            values=list(categories.values()),
            names=list(categories.keys()),
            title="Spending Breakdown (30-day)"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🔄 Recurring Obligations")

        for obligation in health["recurring_obligations"]:
            with st.container():
                col_name, col_amt, col_freq = st.columns([2, 1, 1])
                with col_name:
                    st.write(obligation["name"])
                with col_amt:
                    st.write(f"${obligation['amount']:,.2f}")
                with col_freq:
                    st.write(obligation["frequency"])

        st.info(f"**Total Monthly Fixed Costs:** ${sum(o['amount'] for o in health['recurring_obligations']):,.2f}")

    st.divider()

    # Key insights
    st.subheader("💡 Key Insights")

    for idx, insight in enumerate(health["top_insights"], 1):
        st.info(f"**{idx}. {insight}**")

    st.divider()

    # Recommendations
    st.subheader("🎯 Recommendations")

    health_score = health["health_score"]

    if health_score >= 75:
        st.success("""
        ✅ **Excellent Financial Health**
        - Your finances are in great shape!
        - Maintain current spending patterns
        - Consider setting aside 3-6 months emergency fund
        """)
    elif health_score >= 60:
        st.warning("""
        🟡 **Good Financial Health with Room for Improvement**
        - Try to reduce discretionary spending by 5-10%
        - Increase income stability through side income
        - Monitor credit card usage
        """)
    else:
        st.error("""
        🔴 **Financial Stress Detected**
        - Urgent: Reduce monthly expenses
        - Create a 3-month budget plan
        - Consider consolidating debts
        - Reach out to a financial advisor
        """)
