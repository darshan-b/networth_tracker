"""Overview tab for stock portfolio analysis.

This module provides comprehensive portfolio overview metrics and visualizations.
"""

from typing import List
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from config import ChartConfig
from ui.charts import create_cost_basis_comparison
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_metric_card,
    render_page_hero,
    render_section_intro,
)


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
        inject_surface_styles()
        render_page_hero(
            "Stocks",
            "Overview",
            "Review the current filtered portfolio, contribution context, and period movement.",
            "Holdings stay brokerage/account aware so duplicate tickers do not collapse into one row.",
        )
        
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
        
        historical_filtered = historical_filtered.copy()
        historical_filtered['position_key'] = (
            historical_filtered['Brokerage'].astype(str)
            + '||' + historical_filtered['Account Name'].astype(str)
            + '||' + historical_filtered['ticker'].astype(str)
        )

        # Get latest data for each distinct position from filtered historical data
        latest_data = (
            historical_filtered.sort_values('Date')
            .groupby(['Brokerage', 'Account Name', 'ticker', 'position_key'])
            .last()
            .reset_index()
        )

        # Keep only currently owned positions
        latest_data = latest_data[latest_data['quantity'] > 0].copy()
        currently_owned = latest_data['position_key'].tolist()

        # Get start data for the same positions
        start_data = (
            historical_filtered.sort_values('Date')
            .groupby('position_key')
            .first()
            .reset_index()
        )
        start_data = start_data[start_data['position_key'].isin(currently_owned)].copy()
        
        if latest_data.empty:
            st.info("No positions found for the selected period.")
            return
        
        # Calculate metrics from historical data
        metrics = _calculate_portfolio_metrics(latest_data)
        period_return = _calculate_period_return(start_data, latest_data)
        
        render_section_intro(
            "Snapshot",
            "Use these cards to compare current value, cost basis, gain/loss, and contribution efficiency for the active filter set.",
        )
        _render_metric_cards(metrics, period_return, time_range, trading_log, latest_data)
        
        # Portfolio Performance Chart
        st.divider()
        render_section_intro(
            "Portfolio Analysis",
            "Track how the filtered portfolio value evolved against total cost basis over the selected period.",
        )
        
        historical_owned = historical_filtered[
            historical_filtered['position_key'].isin(currently_owned)
        ]
        
        fig = create_cost_basis_comparison(historical_owned)
        if fig:
            st.plotly_chart(fig, config={"responsive": True})
        else:
            st.info("Unable to create performance comparison chart.")
        
        # Holdings Table
        render_section_intro(
            "Current Holdings",
            "Latest active positions for the current filter set, kept separate by brokerage and account.",
        )
        _render_holdings_table(latest_data, start_data, time_range)
        
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
    latest = df.copy()
    latest['position_key'] = (
        latest['Brokerage'].astype(str)
        + '||' + latest['Account Name'].astype(str)
        + '||' + latest['ticker'].astype(str)
    )
    latest = latest.sort_values('Date').groupby('position_key').last().reset_index()
    return latest[latest['ticker'].isin(owned_symbols)].copy()


def _get_start_data(df: pd.DataFrame, owned_symbols: List[str]) -> pd.DataFrame:
    """Get start data for owned symbols.
    
    Args:
        df: Historical DataFrame
        owned_symbols: List of currently owned symbols
        
    Returns:
        DataFrame with first data per symbol
    """
    start = df.copy()
    start['position_key'] = (
        start['Brokerage'].astype(str)
        + '||' + start['Account Name'].astype(str)
        + '||' + start['ticker'].astype(str)
    )
    start = start.sort_values('Date').groupby('position_key').first().reset_index()
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


def _get_income_like_mask(trading_log: pd.DataFrame) -> pd.Series:
    """Identify dividend/distribution/credit rows used for income tracking."""
    if 'Transaction Type' not in trading_log.columns:
        return pd.Series(False, index=trading_log.index)

    return trading_log['Transaction Type'].fillna('').astype(str).str.contains(
        'dividend|distribution|credit', case=False, regex=True
    )



def _get_exchange_like_mask(trading_log: pd.DataFrame) -> pd.Series:
    """Identify exchange-style rows that can move basis without being buys."""
    if 'Transaction Type' not in trading_log.columns:
        return pd.Series(False, index=trading_log.index)

    return trading_log['Transaction Type'].fillna('').astype(str).str.contains(
        'exchange', case=False, regex=True
    )


def _calculate_cash_flow_metrics(trading_log: pd.DataFrame) -> dict:
    """Calculate contribution and basis-adjustment metrics from the filtered trading log."""
    if trading_log is None or trading_log.empty:
        return {
            'cash_contrib': 0.0,
            'total_dividends': 0.0,
            'cash_income': 0.0,
            'stock_income': 0.0,
            'stock_income_value': 0.0,
            'exchange_value': 0.0,
            'cash_exchange_value': 0.0,
            'stock_exchange_value': 0.0,
        }

    amount_series = pd.to_numeric(trading_log['Amount'], errors='coerce') if 'Amount' in trading_log.columns else pd.Series(0.0, index=trading_log.index)
    quantity_series = pd.to_numeric(trading_log['Quantity'], errors='coerce') if 'Quantity' in trading_log.columns else pd.Series(0.0, index=trading_log.index)

    buy_mask = trading_log['Transaction Type'].eq('Buy') if 'Transaction Type' in trading_log.columns else pd.Series(False, index=trading_log.index)
    income_mask = _get_income_like_mask(trading_log) & amount_series.gt(0)
    exchange_mask = _get_exchange_like_mask(trading_log) & amount_series.gt(0)
    stock_income_mask = income_mask & quantity_series.gt(0)
    cash_income_mask = income_mask & ~quantity_series.gt(0)
    stock_exchange_mask = exchange_mask & quantity_series.gt(0)
    cash_exchange_mask = exchange_mask & ~quantity_series.gt(0)

    return {
        'cash_contrib': amount_series.loc[buy_mask].sum(),
        'total_dividends': amount_series.loc[income_mask].sum(),
        'cash_income': amount_series.loc[cash_income_mask].sum(),
        'stock_income': amount_series.loc[stock_income_mask].sum(),
        'stock_income_value': quantity_series.loc[stock_income_mask].sum(),
        'exchange_value': amount_series.loc[exchange_mask].sum(),
        'cash_exchange_value': amount_series.loc[cash_exchange_mask].sum(),
        'stock_exchange_value': amount_series.loc[stock_exchange_mask].sum(),
    }


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
        render_metric_card(
            "Total Value",
            f"${metrics['total_value']:,.0f}",
            "Latest snapshot",
            "Current market value across the filtered active positions.",
            "positive",
        )
    
    with col2:
        render_metric_card(
            "Total Cost Basis",
            f"${metrics['total_cost']:,.0f}",
            "Capital at work",
            "Remaining cost basis for the filtered active positions.",
            "neutral",
        )
    
    with col3:
        render_metric_card(
            "Total Gain/Loss",
            f"${metrics['total_gain_loss']:,.0f}",
            f"{metrics['total_gain_loss_pct']:.2f}%",
            "Unrealized gain/loss on the current filtered portfolio.",
            "positive" if metrics['total_gain_loss'] > 0 else "negative" if metrics['total_gain_loss'] < 0 else "neutral",
        )
    
    with col4:
        render_metric_card(
            f"Period Return ({time_range})",
            f"{period_return:.2f}%",
            "Selected range",
            "Change in position value over the chosen overview period.",
            "positive" if period_return > 0 else "negative" if period_return < 0 else "neutral",
        )
    
    # Additional metrics row
    if not trading_log.empty:
        cash_flow_metrics = _calculate_cash_flow_metrics(trading_log)
        cash_contrib = cash_flow_metrics['cash_contrib']
        total_dividends = cash_flow_metrics['total_dividends']
        cash_income = cash_flow_metrics['cash_income']
        stock_income = cash_flow_metrics['stock_income']
        exchange_value = cash_flow_metrics['exchange_value']
        cash_exchange_value = cash_flow_metrics['cash_exchange_value']
        stock_exchange_value = cash_flow_metrics['stock_exchange_value']
        basis_adjustment = metrics['total_cost'] - cash_contrib

        col5, col6, col7 = st.columns(3)

        with col5:
            render_metric_card(
                "Cash Contributions",
                f"${cash_contrib:,.0f}",
                "Filtered buys",
                "Cash put into the filtered holdings from rows marked `Buy`.",
                "neutral",
            )

        with col6:
            adjustment_pct = (basis_adjustment * 100 / cash_contrib) if cash_contrib > 0 else 0
            render_metric_card(
                'Basis vs Contributions',
                f"${basis_adjustment:,.0f}",
                f"{adjustment_pct:.2f}%",
                "Remaining cost basis minus cash contributions. Positive values usually come from reinvested dividends, credits, exchanges, or other share-based additions.",
                "positive" if basis_adjustment > 0 else "negative" if basis_adjustment < 0 else "neutral",
            )

        with col7:
            render_metric_card(
                'Total Dividend/Credit',
                f"${total_dividends:,.0f}",
                "Cash + stock",
                "Positive dividend, distribution, and credit amounts recorded in the filtered trading log.",
                "neutral",
            )

        render_accent_pills(
            [
                ("Cash Income", f"${cash_income:,.0f}"),
                ("Stock Income", f"${stock_income:,.0f}"),
                ("Exchanges", f"${exchange_value:,.0f}"),
                ("Cash Exchanges", f"${cash_exchange_value:,.0f}"),
                ("Stock Exchanges", f"${stock_exchange_value:,.0f}"),
                ("Active Positions", str(len(latest_data))),
                ("Unique Symbols", str(latest_data['ticker'].nunique())),
                ("Accounts", str(latest_data['Account Name'].nunique())),
                ("Brokerages", str(latest_data['Brokerage'].nunique())),
            ]
        )


def _render_holdings_table(
    latest_data: pd.DataFrame,
    start_data: pd.DataFrame,
    time_range: str
) -> None:
    """Render holdings table with detailed position information.
    
    Args:
        latest_data: Latest position data
        start_data: Period start data
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
        start_data[['position_key', 'Current Value']],
        on='position_key',
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
    
    required_columns = [
        'Brokerage', 'ticker', 'Account Name', 'quantity', 'Avg Cost', 'Last Close',
        'Current Value', 'Cost Basis', 'Total Gain/Loss', 'Total Gain/Loss %',
        'Period Return %'
    ]
    missing_columns = [col for col in required_columns if col not in holdings_display.columns]
    if missing_columns:
        st.error(
            "Unable to render holdings table because these columns are missing: "
            + ", ".join(missing_columns)
        )
        return
    
    # Select and rename columns
    holdings_display = holdings_display[required_columns].copy()
    
    holdings_display.columns = [
        'Brokerage', 'ticker', 'Account', 'Quantity', 'Avg Cost', 'Last Price', 
        'Current Value', 'Cost Basis', 'Gain/Loss ($)', 'Gain/Loss (%)', 
        f'{time_range} Return (%)'
    ]
    
    # Display formatted table
    st.dataframe(
        holdings_display.style.format({
            'Quantity': '{:.3f}',
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
        width="stretch",
        height=400
    )
