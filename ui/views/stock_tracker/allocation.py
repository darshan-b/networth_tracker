"""Allocation tab for portfolio analysis.

This module provides asset allocation visualization and gain/loss analysis.
"""

import streamlit as st
import pandas as pd

from ui.charts import create_allocation_chart, create_gain_loss_chart


def render(historical_df: pd.DataFrame) -> None:
    """Render the portfolio allocation tab.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
    """
    try:
        st.header("Portfolio Allocation")
        
        if historical_df.empty:
            st.warning("No historical tracking data available for selected filters.")
            return
        
        # Get latest data for each symbol
        latest_data = (
            historical_df
            .sort_values('Date')
            .groupby('ticker')
            .last()
            .reset_index()
        )
        
        # Filter to currently owned positions
        latest_data = latest_data[latest_data['quantity'] > 0].copy()
        
        if latest_data.empty:
            st.info("No currently owned positions found for selected filters.")
            return
        
        # Display allocation metrics
        _render_allocation_summary(latest_data)
        
        # Display allocation charts
        col1, col2 = st.columns(2)
        
        with col1:
            _render_allocation_pie(latest_data)
        
        with col2:
            _render_gain_loss_bar(latest_data)
        
        # Display allocation table
        st.subheader("Allocation Details")
        _render_allocation_table(latest_data)
        
    except Exception as e:
        st.error(f"Error rendering allocation analysis: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_allocation_summary(data: pd.DataFrame) -> None:
    """Render summary metrics for allocation.
    
    Args:
        data: Latest position data
    """
    total_value = data['Current Value'].sum()
    total_positions = len(data)
    avg_position_size = total_value / total_positions if total_positions > 0 else 0
    
    # Find largest position
    largest = data.loc[data['Current Value'].idxmax()]
    largest_pct = (largest['Current Value'] / total_value * 100) if total_value > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Positions", total_positions)
    
    with col2:
        st.metric("Avg Position Size", f"${avg_position_size:,.2f}")
    
    with col3:
        st.metric("Largest Position", largest['ticker'])
    
    with col4:
        st.metric("Largest %", f"{largest_pct:.1f}%")
    
    st.divider()


def _render_allocation_pie(data: pd.DataFrame) -> None:
    """Render allocation pie chart.
    
    Args:
        data: Latest position data
    """
    try:
        fig = create_allocation_chart(data)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating allocation chart: {str(e)}")


def _render_gain_loss_bar(data: pd.DataFrame) -> None:
    """Render gain/loss bar chart.
    
    Args:
        data: Latest position data
    """
    try:
        fig = create_gain_loss_chart(data)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating gain/loss chart: {str(e)}")


def _render_allocation_table(data: pd.DataFrame) -> None:
    """Render detailed allocation table.
    
    Args:
        data: Latest position data with account information from historical tracking
    """
    # Prepare table data
    table_data = data.copy()
    
    # Calculate allocation percentage
    total_value = table_data['Current Value'].sum()
    table_data['Allocation %'] = (
        (table_data['Current Value'] / total_value * 100) 
        if total_value > 0 else 0
    )
    
    # Select and order columns
    display_columns = [
        'ticker',
        'quantity',
        'Current Value',
        'Allocation %',
        'Total Gain/Loss',
        'Total Gain/Loss %'
    ]
    
    # Add account columns if available
    if 'Brokerage' in table_data.columns:
        display_columns.insert(1, 'Brokerage')
    if 'Account Name' in table_data.columns:
        display_columns.insert(2 if 'Brokerage' in display_columns else 1, 'Account Name')
    
    table_data = table_data[display_columns].copy()
    
    # Rename columns
    rename_map = {
        'ticker': 'ticker',
        'quantity': 'Quantity',
        'Current Value': 'Value',
        'Allocation %': 'Allocation %',
        'Total Gain/Loss': 'Gain/Loss ($)',
        'Total Gain/Loss %': 'Gain/Loss (%)'
    }
    
    table_data.columns = [rename_map.get(col, col) for col in table_data.columns]
    
    # Sort by allocation percentage
    table_data = table_data.sort_values('Allocation %', ascending=False)
    
    # Format specifications
    format_dict = {
        'Quantity': '{:.4f}',
        'Value': '${:,.2f}',
        'Allocation %': '{:.2f}%',
        'Gain/Loss ($)': '${:,.2f}',
        'Gain/Loss (%)': '{:.2f}%'
    }
    
    # Display formatted table
    st.dataframe(
        table_data.style.format(format_dict).background_gradient(
            subset=['Allocation %'],
            cmap='Blues'
        ).background_gradient(
            subset=['Gain/Loss (%)'],
            cmap='RdYlGn',
            vmin=-20,
            vmax=20
        ),
        use_container_width=True,
        height=400
    )
    
    # Display concentration metrics
    st.caption(
        f"**Concentration Analysis:** "
        f"Top 3 positions represent {table_data.head(3)['Allocation %'].sum():.1f}% of portfolio"
    )