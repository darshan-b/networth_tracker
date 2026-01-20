"""Cost basis tab for portfolio analysis.

This module provides cost basis analysis and breakdown by symbol.
"""

import streamlit as st
import pandas as pd

from ui.charts import create_cost_basis_comparison


def render(historical_df: pd.DataFrame) -> None:
    """Render the cost basis analysis tab.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
    """
    try:
        st.header("Cost Basis Analysis")
        
        if historical_df.empty:
            st.info(
                "No historical tracking data available for selected filters. "
                "Run historical_tracking.py to generate this data."
            )
            return
        
        # Display cost basis comparison chart
        st.subheader("Portfolio Cost Basis vs Current Value")
        _render_cost_basis_chart(historical_df)
        
        # Display cost basis breakdown
        st.subheader("Cost Basis Breakdown by Symbol")
        _render_cost_basis_breakdown(historical_df)
        
        # Display cost basis metrics
        st.subheader("Cost Basis Metrics")
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
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Unable to create cost basis comparison chart.")
    except Exception as e:
        st.error(f"Error creating chart: {str(e)}")


def _render_cost_basis_breakdown(df: pd.DataFrame) -> None:
    """Render cost basis breakdown table by symbol.
    
    Args:
        df: Historical DataFrame
    """
    # Get latest data for each symbol
    latest_historical = (
        df
        .sort_values('Date')
        .groupby('ticker')
        .last()
        .reset_index()
    )
    
    if latest_historical.empty:
        st.info("No position data available.")
        return
    
    # Select relevant columns
    cost_breakdown = latest_historical[[
        'ticker', 
        'Cost Basis', 
        'Current Value', 
        'Total Gain/Loss', 
        'Total Gain/Loss %'
    ]].copy()
    
    cost_breakdown.columns = [
        'ticker', 
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
        use_container_width=True,
        hide_index=True,
        height=400
    )


def _render_cost_basis_metrics(df: pd.DataFrame) -> None:
    """Render cost basis summary metrics.
    
    Args:
        df: Historical DataFrame
    """
    # Get latest data
    latest = df.sort_values('Date').groupby('ticker').last().reset_index()
    
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