"""Cost basis tab for portfolio analysis.

This module provides cost basis analysis and breakdown by symbol.
"""

import streamlit as st
import pandas as pd

from config import ChartConfig
from ui.charts import create_cost_basis_comparison
from ui.components.surfaces import inject_surface_styles, render_accent_pills, render_section_intro


def _build_position_key(df: pd.DataFrame) -> pd.Series:
    """Build a stable position key to avoid collapsing same-ticker holdings."""
    return (
        df['Brokerage'].astype(str)
        + '||' + df['Account Name'].astype(str)
        + '||' + df['ticker'].astype(str)
    )


def render(historical_df: pd.DataFrame) -> None:
    """Render the cost basis analysis tab.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
    """
    try:
        inject_surface_styles()
        render_section_intro(
            "Cost Basis Analysis",
            "Compare current value to remaining cost basis with position-aware breakdowns that keep same-ticker holdings separate.",
        )
        
        if historical_df.empty:
            st.info(
                "No historical tracking data available for selected filters. "
                "Run historical_tracking.py to generate this data."
            )
            return
        
        # Display cost basis comparison chart
        render_section_intro(
            "Cost Basis vs Value",
            "Track how aggregate portfolio value and cost basis moved across the selected period.",
        )
        _render_cost_basis_chart(historical_df)
        
        # Display cost basis breakdown
        render_section_intro(
            "Position Breakdown",
            "Inspect remaining basis, current value, and gain/loss at the active-position level.",
        )
        _render_cost_basis_breakdown(historical_df)
        
        # Display cost basis metrics
        render_section_intro(
            "Cost Basis Metrics",
            "Summarize total capital at work and the split between profitable and loss-making positions.",
        )
        _render_cost_basis_metrics(historical_df)
        
    except Exception as e:
        st.error(f"Error rendering cost basis analysis: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_cost_basis_chart(df: pd.DataFrame) -> None:
    """Render cost basis comparison chart.
    
    Args:
        df: Historical DataFrame
    """
    try:
        fig = create_cost_basis_comparison(df)
        if fig:
            st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)
        else:
            st.warning("Unable to create cost basis comparison chart.")
    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")


def _render_cost_basis_breakdown(df: pd.DataFrame) -> None:
    """Render cost basis breakdown table by symbol.
    
    Args:
        df: Historical DataFrame
    """
    latest_historical = df.copy()
    latest_historical['position_key'] = _build_position_key(latest_historical)
    latest_historical['Position'] = (
        latest_historical['ticker'].astype(str)
        + ' | ' + latest_historical['Brokerage'].astype(str)
        + ' | ' + latest_historical['Account Name'].astype(str)
    )
    latest_historical = (
        latest_historical
        .sort_values('Date')
        .groupby('position_key')
        .last()
        .reset_index()
    )
    
    if latest_historical.empty:
        st.info("No position data available.")
        return
    
    # Select relevant columns
    cost_breakdown = latest_historical[[
        'Position',
        'Cost Basis', 
        'Current Value', 
        'Total Gain/Loss', 
        'Total Gain/Loss %'
    ]].copy()
    
    cost_breakdown.columns = [
        'Position',
        'Cost Basis', 
        'Current Value', 
        'Gain/Loss ($)', 
        'Gain/Loss (%)'
    ]
    
    # Sort by cost basis
    cost_breakdown = cost_breakdown.sort_values('Cost Basis', ascending=False)
    
    # Display formatted table
    st.dataframe(
        cost_breakdown.style.format({
            'Cost Basis': '${:,.2f}',
            'Current Value': '${:,.2f}',
            'Gain/Loss ($)': '${:,.2f}',
            'Gain/Loss (%)': '{:.2f}%'
        }).background_gradient(
            subset=['Gain/Loss (%)'],
            cmap='RdYlGn',
            vmin=-20,
            vmax=20
        ),
        width="stretch",
        hide_index=True,
        height=400
    )


def _render_cost_basis_metrics(df: pd.DataFrame) -> None:
    """Render cost basis summary metrics.
    
    Args:
        df: Historical DataFrame
    """
    # Get latest data
    latest = df.copy()
    latest['position_key'] = _build_position_key(latest)
    latest = latest.sort_values('Date').groupby('position_key').last().reset_index()
    
    # Calculate totals
    total_cost = latest['Cost Basis'].sum()
    total_value = latest['Current Value'].sum()
    total_gain = total_value - total_cost
    total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0
    
    # Calculate weighted metrics
    avg_gain_pct = latest['Total Gain/Loss %'].mean()
    
    # Winners vs losers
    winners = latest[latest['Total Gain/Loss'] > 0]
    losers = latest[latest['Total Gain/Loss'] < 0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cost Basis", f"${total_cost:,.2f}")
    
    with col2:
        st.metric("Total Current Value", f"${total_value:,.2f}")
    
    with col3:
        st.metric(
            "Total Gain/Loss", 
            f"${total_gain:,.2f}",
            delta=f"{total_gain_pct:.2f}%"
        )
    
    with col4:
        st.metric("Avg Gain/Loss %", f"{avg_gain_pct:.2f}%")
    
    # Winner/Loser breakdown
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Profitable Positions")
        if not winners.empty:
            winner_count = len(winners)
            winner_value = winners['Total Gain/Loss'].sum()
            winner_pct = (winner_count / len(latest) * 100) if len(latest) > 0 else 0
            
            st.metric("Count", winner_count)
            st.metric("Total Gain", f"${winner_value:,.2f}")
            st.caption(f"{winner_pct:.1f}% of positions")
        else:
            st.info("No profitable positions")
    
    with col2:
        st.markdown("#### Loss-Making Positions")
        if not losers.empty:
            loser_count = len(losers)
            loser_value = abs(losers['Total Gain/Loss'].sum())
            loser_pct = (loser_count / len(latest) * 100) if len(latest) > 0 else 0
            
            st.metric("Count", loser_count)
            st.metric("Total Loss", f"${loser_value:,.2f}")
            st.caption(f"{loser_pct:.1f}% of positions")
        else:
            st.info("No loss-making positions")

    render_accent_pills(
        [
            ("Positions", str(len(latest))),
            ("Winners", str(len(winners))),
            ("Losers", str(len(losers))),
            ("Accounts", str(latest['Account Name'].nunique()) if 'Account Name' in latest.columns else "N/A"),
        ]
    )
