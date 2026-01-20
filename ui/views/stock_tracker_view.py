"""Stock Tracker view module.

This module provides the main view for stock portfolio tracking and analysis,
using only Historical Tracking data (no Summary or Tracking sheets needed).
"""

from typing import List, Tuple
from datetime import datetime

import pandas as pd
import streamlit as st

from ui.components.filters import render_stock_header_filters, render_stock_sidebar_filters
from ui.views.stock_tracker import (
    overview, 
    performance, 
    allocation, 
    risk_analysis, 
    transactions, 
    cost_basis
)


def _filter_by_header_selections(
    df: pd.DataFrame, 
    selected_brokerages: List[str],
    selected_accounts: List[str],
    selected_types: List[str]
) -> pd.DataFrame:
    """Filter historical data by brokerage, account, and investment type selections.
    
    Args:
        df: Historical tracking DataFrame with Brokerage, Account Name, Investment Type columns
        selected_brokerages: List of brokerages to include
        selected_accounts: List of account names to include
        selected_types: List of investment types to include
        
    Returns:
        Filtered DataFrame
    """
    if not selected_brokerages and not selected_accounts and not selected_types:
        return pd.DataFrame()
    
    # Build filter conditions
    conditions = []
    
    if selected_brokerages and 'Brokerage' in df.columns:
        conditions.append(df['Brokerage'].isin(selected_brokerages))
    
    if selected_accounts and 'Account Name' in df.columns:
        conditions.append(df['Account Name'].isin(selected_accounts))
    
    if selected_types and 'Investment Type' in df.columns:
        conditions.append(df['Investment Type'].isin(selected_types))
    
    # Apply all conditions with AND logic
    if conditions:
        mask = conditions[0]
        for condition in conditions[1:]:
            mask = mask & condition
        
        return df[mask].copy()
    
    return df.copy()


def _filter_by_date_range(
    df: pd.DataFrame,
    date_range: Tuple[datetime, datetime]
) -> pd.DataFrame:
    """Filter DataFrame by date range.
    
    Args:
        df: DataFrame with date column
        date_range: Tuple of (start_date, end_date)
        
    Returns:
        Filtered DataFrame
    """
    if len(date_range) != 2 or date_range[0] is None or date_range[1] is None:
        return df
    
    # Find date column (case-insensitive)
    date_col = None
    for col in df.columns:
        if col.lower() == 'date':
            date_col = col
            break
    
    if date_col is None or date_col not in df.columns:
        return df
    
    start_date, end_date = date_range
    
    return df[
        (df[date_col].dt.date >= start_date) & 
        (df[date_col].dt.date <= end_date)
    ].copy()


def _get_filtered_symbols(
    historical_df: pd.DataFrame
) -> List[str]:
    """Get list of currently owned symbols from historical data.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
        
    Returns:
        List of symbol tickers that are currently owned (quantity > 0)
    """
    # Find required columns (case-insensitive)
    date_col = None
    ticker_col = None
    quantity_col = None
    
    for col in historical_df.columns:
        col_lower = col.lower()
        if col_lower == 'date':
            date_col = col
        elif col_lower in ['ticker', 'symbol']:
            ticker_col = col
        elif col_lower == 'quantity':
            quantity_col = col
    
    # Validate all required columns exist
    if date_col is None or ticker_col is None or quantity_col is None:
        return []
    
    # Get latest data for each symbol
    try:
        latest_data = (
            historical_df
            .sort_values(date_col)
            .groupby(ticker_col)
            .last()
            .reset_index()
        )
        
        # Get currently owned symbols (quantity > 0)
        currently_owned = latest_data[
            latest_data[quantity_col] > 0
        ][ticker_col].unique().tolist()
        
        return sorted(currently_owned)
    except Exception:
        return []


def _display_filter_summary(
    selected_brokerages: List[str],
    selected_accounts: List[str],
    selected_types: List[str],
    filtered_symbols: List[str],
    date_range: Tuple[datetime, datetime]
) -> None:
    """Display summary of applied filters.
    
    Args:
        selected_brokerages: List of selected brokerages
        selected_accounts: List of selected account names
        selected_types: List of selected investment types
        filtered_symbols: List of symbols after all filters applied
        date_range: Selected date range
    """
    with st.expander("📋 Active Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Brokerages", len(selected_brokerages))
            if selected_brokerages and len(selected_brokerages) <= 3:
                st.caption(", ".join(selected_brokerages))
            elif selected_brokerages:
                st.caption(f"{', '.join(selected_brokerages[:2])}, +{len(selected_brokerages)-2} more")
            else:
                st.caption("All")
        
        with col2:
            st.metric("Accounts", len(selected_accounts))
            if selected_accounts and len(selected_accounts) <= 3:
                st.caption(", ".join(selected_accounts))
            elif selected_accounts:
                st.caption(f"{', '.join(selected_accounts[:2])}, +{len(selected_accounts)-2} more")
            else:
                st.caption("All")
        
        with col3:
            st.metric("Types", len(selected_types))
            if selected_types and len(selected_types) <= 3:
                st.caption(", ".join(selected_types))
            elif selected_types:
                st.caption(f"{', '.join(selected_types[:2])}, +{len(selected_types)-2} more")
            else:
                st.caption("All")
        
        with col4:
            st.metric("Positions", len(filtered_symbols))
            if len(filtered_symbols) <= 5:
                st.caption(", ".join(filtered_symbols))
            else:
                st.caption(f"{', '.join(filtered_symbols[:3])}, +{len(filtered_symbols)-3} more")
        
        # Date range info
        if len(date_range) == 2 and date_range[0] and date_range[1]:
            days = (date_range[1] - date_range[0]).days + 1
            st.caption(f"📅 Date Range: {date_range[0]} to {date_range[1]} ({days} days)")
        else:
            st.caption("📅 Date Range: All")


def show_stock_tracker(
    trading_log: pd.DataFrame, 
    historical: pd.DataFrame
) -> None:
    """Render the Stock Tracker view with filtering and analytics.
    
    This function works entirely from Historical Tracking data.
    No Summary or Tracking sheets are needed.
    
    Args:
        trading_log: Trading log DataFrame with transaction history (optional)
        historical: Historical tracking DataFrame with these required columns:
            - Date (or date)
            - ticker or Symbol
            - quantity
            - Last Close, Current Value, Cost Basis
            - Total Gain/Loss, Total Gain/Loss %
            - Brokerage
            - Account Name
            - Investment Type
    """
    try:
        st.title("📈 Portfolio Analysis Dashboard")
        
        # Validate historical data exists
        if historical is None or historical.empty:
            st.error(
                "Historical tracking data not found. "
                "Please ensure your Historical_Tracking sheet has data."
            )
            st.info(
                "Required columns: Date, ticker (or Symbol), quantity, Last Close, "
                "Current Value, Cost Basis, Total Gain/Loss, Total Gain/Loss %, "
                "Brokerage, Account Name, Investment Type"
            )
            return
        
        # Validate required columns (case-insensitive)
        required_columns = {
            'date': 'Date',
            'ticker': 'ticker (or Symbol)',
            'quantity': 'quantity',
            'brokerage': 'Brokerage',
            'account name': 'Account Name',
            'investment type': 'Investment Type'
        }
        
        # Create mapping of lowercase to actual column names
        col_mapping = {col.lower(): col for col in historical.columns}
        
        missing = []
        for req_col_lower, req_col_display in required_columns.items():
            # Check for ticker/symbol special case
            if req_col_lower == 'ticker':
                if 'ticker' not in col_mapping and 'symbol' not in col_mapping:
                    missing.append(req_col_display)
            elif req_col_lower not in col_mapping:
                missing.append(req_col_display)
        
        if missing:
            st.error(historical.columns)
            st.error(
                f"Historical tracking data is missing required columns: {', '.join(missing)}"
            )
            st.info(
                "Please add these columns to your Historical_Tracking sheet: "
                "Brokerage, Account Name, Investment Type"
            )
            with st.expander("📋 Available columns in your data"):
                st.write(list(historical.columns))
            return
        
        # Render header filters (brokerage, account name, investment type)
        selected_brokerages, selected_accounts, selected_types = render_stock_header_filters(
            historical
        )
        
        # Validate header filters
        if not selected_brokerages and not selected_accounts and not selected_types:
            st.info("Please select at least one brokerage, account, or investment type to view portfolio data.")
            return
        
        # Render sidebar filters (date range)
        date_range = render_stock_sidebar_filters(
            historical,
            selected_brokerages,
            selected_accounts,
            selected_types
        )
        
        # Apply header filters to historical data
        historical_filtered = _filter_by_header_selections(
            historical, 
            selected_brokerages,
            selected_accounts,
            selected_types
        )
        
        if historical_filtered.empty:
            st.warning("No data available for the selected brokerages, accounts, and investment types.")
            return
        
        # Apply date range filter to historical data
        historical_filtered = _filter_by_date_range(historical_filtered, date_range)
        
        if historical_filtered.empty:
            st.warning("No data available for the selected date range.")
            return
        
        # Get filtered symbols (currently owned positions)
        filtered_symbols = _get_filtered_symbols(historical_filtered)
        
        if not filtered_symbols:
            st.info("No currently owned positions found for the selected filters.")
            return
        
        # Filter trading log by selected symbols
        if trading_log is not None and not trading_log.empty:
            try:
                trading_log_filtered = trading_log[
                    trading_log['ticker'].isin(filtered_symbols)
                ].copy()
            except Exception:
                trading_log_filtered = pd.DataFrame()
        else:
            trading_log_filtered = pd.DataFrame()
        
        # Display filter summary
        _display_filter_summary(
            selected_brokerages,
            selected_accounts,
            selected_types,
            filtered_symbols, 
            date_range
        )
        
        # Create tabs for different analyses
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Overview",
            "📈 Performance",
            "🥧 Allocation",
            "⚠️ Risk Analysis",
            "💰 Transactions",
            "💵 Cost Basis"
        ])
        
        with tab1:
            overview.render(
                historical_filtered, 
                filtered_symbols,
                trading_log_filtered
            )
        
        with tab2:
            performance.render(historical_filtered, filtered_symbols)
        
        with tab3:
            allocation.render(historical_filtered)
        
        with tab4:
            risk_analysis.render(historical_filtered, filtered_symbols)
        
        with tab5:
            transactions.render(trading_log_filtered)
        
        with tab6:
            cost_basis.render(historical_filtered)
            
    except Exception as e:
        st.error(f"An error occurred while loading the Stock Tracker: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.exception(e)