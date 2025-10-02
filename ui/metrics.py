"""UI components for metric display."""

import streamlit as st


def render_key_metrics(metrics, previous_month_exists):
    """Render the 3 main KPI metric cards.
    
    Args:
        metrics: Dictionary containing calculated metrics
        previous_month_exists: Boolean indicating if previous month data is available
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Net Worth",
            value=f"${metrics['current_net_worth']:,.0f}",
            delta=f"{metrics['net_worth_pct_change']:+.2f}%" if previous_month_exists else None
        )
    
    with col2:
        st.metric(
            label="Total Liabilities",
            value=f"${metrics['current_liabilities']:,.0f}",
            delta=f"{metrics['liabilities_change_pct']:+.2f}%" if previous_month_exists else None,
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            label="Debt Ratio",
            value=f"{metrics['debt_ratio']:.1f}%"
        )
