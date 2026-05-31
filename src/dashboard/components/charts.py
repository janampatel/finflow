"""Reusable Plotly chart components for dashboard."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Optional


def create_health_gauge(score: float, min_val: float = 0, max_val: float = 100) -> go.Figure:
    """Create a gauge chart for financial health score.

    Args:
        score: Current score value
        min_val: Minimum gauge value
        max_val: Maximum gauge value

    Returns:
        Plotly figure with gauge chart
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Health Score"},
        gauge={
            "axis": {"range": [min_val, max_val]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [min_val, max_val * 0.4], "color": "#ffcccc"},
                {"range": [max_val * 0.4, max_val * 0.7], "color": "#fff3cd"},
                {"range": [max_val * 0.7, max_val], "color": "#d4edda"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": max_val * 0.85
            }
        }
    ))

    return fig


def create_anomaly_distribution(df: pd.DataFrame, x_col: str, color_col: str) -> go.Figure:
    """Create histogram showing anomaly score distribution.

    Args:
        df: DataFrame with anomaly data
        x_col: Column for x-axis (anomaly scores)
        color_col: Column for color coding (severity)

    Returns:
        Plotly histogram figure
    """
    color_map = {
        "high": "#d32f2f",
        "medium": "#fbc02d",
        "low": "#388e3c"
    }

    fig = px.histogram(
        df,
        x=x_col,
        nbins=15,
        color=color_col,
        color_discrete_map=color_map,
        title="Anomaly Score Distribution",
        labels={x_col: "Anomaly Score", color_col: "Severity"}
    )

    return fig


def create_category_pie(category_dict: Dict[str, float], title: str = "Distribution") -> go.Figure:
    """Create pie chart for category distribution.

    Args:
        category_dict: Dict mapping category names to values
        title: Chart title

    Returns:
        Plotly pie figure
    """
    fig = px.pie(
        values=list(category_dict.values()),
        names=list(category_dict.keys()),
        title=title
    )

    return fig


def create_timeseries(df: pd.DataFrame, date_col: str, value_col: str,
                     title: str = "Time Series", label: str = "Value") -> go.Figure:
    """Create line chart for time series data.

    Args:
        df: DataFrame with time series data
        date_col: Column name for dates
        value_col: Column name for values
        title: Chart title
        label: Y-axis label

    Returns:
        Plotly line figure
    """
    fig = px.line(
        df,
        x=date_col,
        y=value_col,
        title=title,
        labels={value_col: label}
    )

    return fig


def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str,
                    title: str = "Distribution", color_col: Optional[str] = None) -> go.Figure:
    """Create bar chart for categorical data.

    Args:
        df: DataFrame with data
        x_col: Column for x-axis
        y_col: Column for y-axis
        title: Chart title
        color_col: Optional column for color coding

    Returns:
        Plotly bar figure
    """
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        title=title,
        labels={y_col: "Count"}
    )

    return fig


def create_donut_chart(category_dict: Dict[str, float], title: str = "Distribution") -> go.Figure:
    """Create donut chart for spending breakdown.

    Args:
        category_dict: Dict mapping category names to amounts
        title: Chart title

    Returns:
        Plotly donut figure
    """
    fig = px.pie(
        values=list(category_dict.values()),
        names=list(category_dict.keys()),
        title=title,
        hole=0.4
    )

    return fig


def create_box_plot(df: pd.DataFrame, x_col: str, y_col: str,
                   title: str = "Distribution") -> go.Figure:
    """Create box plot for value distributions.

    Args:
        df: DataFrame with data
        x_col: Column for x-axis (categories)
        y_col: Column for y-axis (values)
        title: Chart title

    Returns:
        Plotly box plot figure
    """
    fig = px.box(
        df,
        x=x_col,
        y=y_col,
        title=title,
        labels={y_col: "Value"}
    )

    return fig


def create_scatter_plot(df: pd.DataFrame, x_col: str, y_col: str,
                       color_col: Optional[str] = None,
                       title: str = "Scatter Plot") -> go.Figure:
    """Create scatter plot.

    Args:
        df: DataFrame with data
        x_col: Column for x-axis
        y_col: Column for y-axis
        color_col: Optional column for color coding
        title: Chart title

    Returns:
        Plotly scatter figure
    """
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        title=title
    )

    return fig
