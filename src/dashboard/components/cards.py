"""Reusable metric card components for dashboard."""

import streamlit as st
from typing import Optional


def render_metric_card(title: str, value: str, delta: Optional[str] = None,
                      icon: str = "📊", color: str = "normal") -> None:
    """Render a styled metric card.

    Args:
        title: Card title
        value: Main metric value
        delta: Optional delta indicator (e.g., "+12%")
        icon: Emoji icon for card
        color: Color scheme ("normal", "success", "warning", "danger")

    Returns:
        None (renders to Streamlit)
    """
    color_styles = {
        "normal": "#f0f2f6",
        "success": "#d4edda",
        "warning": "#fff3cd",
        "danger": "#ffcccc"
    }

    bg_color = color_styles.get(color, color_styles["normal"])

    html = f"""
    <div style="
        background-color: {bg_color};
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid {'#28a745' if color == 'success' else '#ffc107' if color == 'warning' else '#dc3545' if color == 'danger' else '#0066cc'};
    ">
        <h4 style="margin: 0 0 10px 0;">{icon} {title}</h4>
        <p style="margin: 0; font-size: 24px; font-weight: bold;">{value}</p>
        {'<p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">' + delta + '</p>' if delta else ''}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_status_card(title: str, status: str, description: str = "") -> None:
    """Render a status indicator card.

    Args:
        title: Card title
        status: Status text (e.g., "Healthy", "Warning", "Critical")
        description: Optional description text

    Returns:
        None (renders to Streamlit)
    """
    status_colors = {
        "healthy": ("#28a745", "🟢"),
        "warning": ("#ffc107", "🟡"),
        "critical": ("#dc3545", "🔴"),
        "active": ("#0066cc", "🔵")
    }

    color, emoji = status_colors.get(status.lower(), ("#999", "⚪"))

    html = f"""
    <div style="
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid {color};
    ">
        <h4 style="margin: 0 0 10px 0;">{emoji} {title}</h4>
        <p style="margin: 0; font-size: 16px; color: {color}; font-weight: bold;">{status}</p>
        {'<p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">' + description + '</p>' if description else ''}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_alert(message: str, alert_type: str = "info") -> None:
    """Render an alert box.

    Args:
        message: Alert message
        alert_type: Type of alert ("info", "success", "warning", "error")

    Returns:
        None (renders to Streamlit)
    """
    alert_styles = {
        "info": ("#d1ecf1", "#0c5460", "ℹ️"),
        "success": ("#d4edda", "#155724", "✅"),
        "warning": ("#fff3cd", "#856404", "⚠️"),
        "error": ("#f8d7da", "#721c24", "❌")
    }

    bg_color, text_color, icon = alert_styles.get(alert_type, alert_styles["info"])

    html = f"""
    <div style="
        background-color: {bg_color};
        color: {text_color};
        padding: 15px;
        border-radius: 4px;
        margin: 10px 0;
        border-left: 4px solid {text_color};
    ">
        <p style="margin: 0;"><strong>{icon} {message}</strong></p>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_info_box(title: str, content: str, icon: str = "💡") -> None:
    """Render an information box.

    Args:
        title: Box title
        content: Box content text
        icon: Emoji icon

    Returns:
        None (renders to Streamlit)
    """
    html = f"""
    <div style="
        background-color: #e7f3ff;
        border: 1px solid #b3d9ff;
        padding: 15px;
        border-radius: 4px;
        margin: 10px 0;
    ">
        <h5 style="margin: 0 0 8px 0;">{icon} {title}</h5>
        <p style="margin: 0; font-size: 14px; color: #333;">{content}</p>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_progress_card(title: str, progress: float, target: float = 100.0,
                        unit: str = "%") -> None:
    """Render a progress card with visual bar.

    Args:
        title: Card title
        progress: Current progress value
        target: Target value
        unit: Unit label

    Returns:
        None (renders to Streamlit)
    """
    pct = min(100, (progress / target) * 100) if target > 0 else 0

    html = f"""
    <div style="
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
    ">
        <h4 style="margin: 0 0 10px 0;">{title}</h4>
        <div style="background-color: #e0e0e0; border-radius: 4px; height: 24px; overflow: hidden;">
            <div style="
                background-color: {'#28a745' if pct >= 75 else '#ffc107' if pct >= 50 else '#dc3545'};
                width: {pct}%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 12px;
            ">
                {pct:.0f}%
            </div>
        </div>
        <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
            {progress:.1f} / {target:.1f} {unit}
        </p>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
