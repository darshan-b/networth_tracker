"""Overview tab for stock portfolio analysis.

This module provides comprehensive portfolio overview metrics and visualizations.
"""

from typing import List
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from ui.charts import create_cost_basis_comparison


def get_date_range(period: str, end_date: datetime) -> datetime:
    """Calculate start date based on period selection.
    
    Args:
        period: Time period string ('1M', '3M', '6M', 'YTD', '1Y', '3Y', 'All')
        end_date: End date for the range
        
    Returns:
        Start date for the period, or None for 'All'
    """
    period_map = {
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "3Y": 1095
    }
    
    if period == "YTD":
        return datetime(end_date.year, 1, 1)
    elif period == "All":
        return None
    else:
        days = period_map.get(period, 0)
        return end_date - timedelta(days=days)


def render(
    historical_df: pd.DataFrame,
    selected_symbols: List[str],
    trading_log: pd.DataFrame
) -> None:
    """Render the portfolio overview tab.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
        selected_symbols: List of selected symbols
        trading_log: Trading log DataFrame (already filtered)
    """
    try:
        st.header("Portfolio Overview")
        
        if historical_df.empty:
            st.warning("No historical tracking data available for selected filters.")
            return
        
        # Time range selector
        _render_time_range_selector()
        
        time_range = st.session_state.get('time_range', 'All')
        
        # Filter data by time range
        historical_filtered = _apply_time_filter(historical_df, time_range)
        
        if historical_filtered.empty:
            st.warning(f"No data available for the selected time range ({time_range}).")
            return
        
        # Get latest data for each symbol from filtered historical data
        latest_data = historical_filtered.sort_values('Date').groupby(['Brokerage', 'Account Name', 'ticker']).last().reset_index()
        
        # Get currently owned symbols (quantity > 0)
        currently_owned = latest_data[latest_data['quantity'] > 0]['ticker'].tolist()
        
        # Filter to only currently owned
        latest_data = latest_data[latest_data['ticker'].isin(currently_owned)].copy()
        
        # Get start data for period
        start_data = historical_filtered.sort_values('Date').groupby('ticker').first().reset_index()
        start_data = start_data[start_data['ticker'].isin(currently_owned)].copy()
        
        if latest_data.empty:
            st.info("No positions found for the selected period.")
            return
        
        # Calculate metrics from historical data
        metrics = _calculate_portfolio_metrics(latest_data)
        period_return = _calculate_period_return(start_data, latest_data)
        
        _render_metric_cards(metrics, period_return, time_range, trading_log, latest_data)
        
        # Portfolio Performance Chart
        st.header("Portfolio Analysis")
        
        historical_owned = historical_filtered[
            historical_filtered['ticker'].isin(currently_owned)
        ]
        
        fig = create_cost_basis_comparison(historical_owned)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Unable to create performance comparison chart.")
        
        # Holdings Table
        st.header("Current Holdings")
        _render_holdings_table(latest_data, start_data, historical_filtered, time_range)
        
    except Exception as e:
        st.error(f"Error rendering overview: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_time_range_selector() -> None:
    """Render time range selection radio buttons."""
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        time_range = st.radio(
            "Time Range",
            options=["1M", "3M", "6M", "YTD", "1Y", "3Y", "All"],
            index=6,
            horizontal=True,
            key='time_range'
        )


def _apply_time_filter(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    """Apply time range filter to DataFrame.
    
    Args:
        df: DataFrame to filter
        time_range: Time period string
        
    Returns:
        Filtered DataFrame
    """
    end_date = df['Date'].max()
    start_date = get_date_range(time_range, end_date)
    
    if start_date:
        return df[df['Date'] >= start_date].copy()
    return df.copy()


def _calculate_portfolio_metrics(latest_data: pd.DataFrame) -> dict:
    """Calculate portfolio metrics from latest historical data.
    
    Args:
        latest_data: DataFrame with latest data for each symbol
        
    Returns:
        Dictionary of portfolio metrics
    """
    st.dataframe(latest_data)
    total_value = latest_data['Current Value'].sum()
    total_cost = latest_data['Cost Basis'].sum()
    total_gain_loss = latest_data['Total Gain/Loss'].sum()
    total_gain_loss_pct = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
    
    return {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_gain_loss': total_gain_loss,
        'total_gain_loss_pct': total_gain_loss_pct
    }


def _get_latest_data(df: pd.DataFrame, owned_symbols: List[str]) -> pd.DataFrame:
    """Get latest data for owned symbols.
    
    Args:
        df: Historical DataFrame
        owned_symbols: List of currently owned symbols
        
    Returns:
        DataFrame with latest data per symbol
    """
    latest = df.sort_values('Date').groupby('ticker').last().reset_index()
    return latest[latest['ticker'].isin(owned_symbols)].copy()


def _get_start_data(df: pd.DataFrame, owned_symbols: List[str]) -> pd.DataFrame:
    """Get start data for owned symbols.
    
    Args:
        df: Historical DataFrame
        owned_symbols: List of currently owned symbols
        
    Returns:
        DataFrame with first data per symbol
    """
    start = df.sort_values('Date').groupby('ticker').first().reset_index()
    return start[start['ticker'].isin(owned_symbols)].copy()


def _calculate_period_return(start_data: pd.DataFrame, latest_data: pd.DataFrame) -> float:
    """Calculate portfolio return for the period.
    
    Args:
        start_data: DataFrame with period start values
        latest_data: DataFrame with current values
        
    Returns:
        Period return as percentage
    """
    start_value = start_data['Current Value'].sum()
    end_value = latest_data['Current Value'].sum()
    
    if start_value > 0:
        return ((end_value - start_value) / start_value * 100)
    return 0.0


def _render_metric_cards(
    metrics: dict,
    period_return: float,
    time_range: str,
    trading_log: pd.DataFrame,
    latest_data: pd.DataFrame
) -> None:
    """Render metric cards for portfolio overview.
    
    Args:
        metrics: Dictionary of calculated metrics
        period_return: Period return percentage
        time_range: Selected time range string
        trading_log: Trading log DataFrame
        latest_data: Latest position data
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Value",
            f"${metrics['total_value']:,.2f}"
        )
    
    with col2:
        st.metric(
            "Total Cost Basis",
            f"${metrics['total_cost']:,.2f}"
        )
    
    with col3:
        st.metric(
            "Total Gain/Loss",
            f"${metrics['total_gain_loss']:,.2f}",
            delta=f"{metrics['total_gain_loss_pct']:.2f}%"
        )
    
    with col4:
        st.metric(
            f"Period Return ({time_range})",
            f"{period_return:.2f}%"
        )
    
    # Additional metrics row
    if not trading_log.empty:
        col5, col6 = st.columns(2)
        
        total_contrib = trading_log[
            trading_log['Transaction Type'] == 'Buy'
        ]['Amount'].sum()
        
        with col5:
            st.metric(
                "Total Contributions", 
                f"${total_contrib:,.2f}"
            )
        
        with col6:
            gain_on_contrib = metrics['total_value'] - total_contrib
            gain_pct = (gain_on_contrib * 100 / total_contrib) if total_contrib > 0 else 0
            st.metric(
                'Gain on Contributions',
                f"${gain_on_contrib:,.2f}",
                delta=f"{gain_pct:.2f}%"
            )


def _render_holdings_table(
    latest_data: pd.DataFrame,
    start_data: pd.DataFrame,
    summary_df: pd.DataFrame,
    time_range: str
) -> None:
    """Render holdings table with detailed position information.
    
    Args:
        latest_data: Latest position data
        start_data: Period start data
        summary_df: Summary DataFrame
        time_range: Selected time range string
    """
    holdings_display = latest_data[latest_data['quantity'] > 0].copy()
    if holdings_display.empty:
        st.info("No holdings to display for the selected period.")
        return
    
    # Calculate average cost
    holdings_display['Avg Cost'] = (
        holdings_display['Cost Basis'] / holdings_display['quantity']
    )
    
    # Calculate period performance
    holdings_display = holdings_display.merge(
        start_data[['ticker', 'Current Value']],
        on='ticker',
        how='left',
        suffixes=('', '_start')
    )
    
    holdings_display['Period Return %'] = holdings_display.apply(
        lambda row: (
            ((row['Current Value'] - row['Current Value_start']) / 
             row['Current Value_start'] * 100)
            if pd.notna(row['Current Value_start']) and row['Current Value_start'] > 0 
            else 0
        ),
        axis=1
    )
    
    # Add account information
    holdings_display = holdings_display.merge(
        summary_df[['ticker', 'Account Name']],
        left_on='ticker',
        right_on='ticker',
        how='left'
    )
    
    # Select and rename columns
    holdings_display = holdings_display[[
        'ticker', 'Account Name', 'quantity', 'Avg Cost', 'Last Close', 
        'Current Value', 'Cost Basis', 'Total Gain/Loss', 'Total Gain/Loss %', 
        'Period Return %'
    ]].copy()
    
    holdings_display.columns = [
        'ticker', 'Account', 'Quantity', 'Avg Cost', 'Last Price', 
        'Current Value', 'Cost Basis', 'Gain/Loss ($)', 'Gain/Loss (%)', 
        f'{time_range} Return (%)'
    ]
    
    # Display formatted table
    st.dataframe(
        holdings_display.style.format({
            'Quantity': '{:.4f}',
            'Avg Cost': '${:.2f}',
            'Last Price': '${:.2f}',
            'Current Value': '${:,.2f}',
            'Cost Basis': '${:,.2f}',
            'Gain/Loss ($)': '${:,.2f}',
            'Gain/Loss (%)': '{:.2f}%',
            f'{time_range} Return (%)': '{:.2f}%'
        }).background_gradient(
            subset=['Gain/Loss (%)'],
            cmap='RdYlGn',
            vmin=-20,
            vmax=20
        ),
        use_container_width=True,
        height=400
    )