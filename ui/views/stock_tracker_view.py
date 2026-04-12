"""Stock Tracker view module.

This module provides the main view for stock portfolio tracking and analysis,
using only Historical Tracking data (no Summary or Tracking sheets needed).
"""

from datetime import datetime
from typing import List, Tuple

import pandas as pd
import streamlit as st

from config import StockTrackerConfig
from constants import StockColumnNames
from ui.components.filters import render_stock_header_filters, render_stock_sidebar_filters
from ui.views.stock_tracker import (
    allocation,
    cost_basis,
    overview,
    performance,
    risk_analysis,
    transactions,
)


def _filter_by_header_selections(
    df: pd.DataFrame,
    selected_brokerages: List[str],
    selected_accounts: List[str],
    selected_types: List[str],
) -> pd.DataFrame:
    """Filter historical data by brokerage, account, and investment type selections."""
    if not selected_brokerages and not selected_accounts and not selected_types:
        return pd.DataFrame()

    conditions = []

    if selected_brokerages and StockColumnNames.BROKERAGE in df.columns:
        conditions.append(df[StockColumnNames.BROKERAGE].isin(selected_brokerages))

    if selected_accounts and StockColumnNames.ACCOUNT_NAME in df.columns:
        conditions.append(df[StockColumnNames.ACCOUNT_NAME].isin(selected_accounts))

    if selected_types and StockColumnNames.INVESTMENT_TYPE in df.columns:
        conditions.append(df[StockColumnNames.INVESTMENT_TYPE].isin(selected_types))

    if conditions:
        mask = conditions[0]
        for condition in conditions[1:]:
            mask = mask & condition
        return df[mask].copy()

    return df.copy()


def _filter_by_date_range(
    df: pd.DataFrame,
    date_range: Tuple[datetime, datetime],
) -> pd.DataFrame:
    """Filter DataFrame by date range."""
    if len(date_range) != 2 or date_range[0] is None or date_range[1] is None:
        return df

    date_col = None
    for col in df.columns:
        if col.lower() == "date":
            date_col = col
            break

    if date_col is None or date_col not in df.columns:
        return df

    start_date, end_date = date_range
    return df[
        (df[date_col].dt.date >= start_date)
        & (df[date_col].dt.date <= end_date)
    ].copy()


def _get_filtered_symbols(historical_df: pd.DataFrame) -> List[str]:
    """Get list of currently owned symbols from historical data."""
    date_col = None
    ticker_col = None
    quantity_col = None

    for col in historical_df.columns:
        col_lower = col.lower()
        if col_lower == StockColumnNames.DATE.lower():
            date_col = col
        elif col_lower in [StockColumnNames.TICKER.lower(), StockColumnNames.SYMBOL.lower()]:
            ticker_col = col
        elif col_lower == StockColumnNames.QUANTITY.lower():
            quantity_col = col

    if date_col is None or ticker_col is None or quantity_col is None:
        return []

    try:
        latest_data = (
            historical_df
            .sort_values(date_col)
            .groupby(ticker_col)
            .last()
            .reset_index()
        )
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
    date_range: Tuple[datetime, datetime],
) -> None:
    """Display summary of applied filters."""
    with st.expander(StockTrackerConfig.FILTER_SUMMARY_TITLE, expanded=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Brokerages", len(selected_brokerages))
            if selected_brokerages and len(selected_brokerages) <= 3:
                st.caption(", ".join(selected_brokerages))
            elif selected_brokerages:
                st.caption(f"{', '.join(selected_brokerages[:2])}, +{len(selected_brokerages) - 2} more")
            else:
                st.caption("All")

        with col2:
            st.metric("Accounts", len(selected_accounts))
            if selected_accounts and len(selected_accounts) <= 3:
                st.caption(", ".join(selected_accounts))
            elif selected_accounts:
                st.caption(f"{', '.join(selected_accounts[:2])}, +{len(selected_accounts) - 2} more")
            else:
                st.caption("All")

        with col3:
            st.metric("Types", len(selected_types))
            if selected_types and len(selected_types) <= 3:
                st.caption(", ".join(selected_types))
            elif selected_types:
                st.caption(f"{', '.join(selected_types[:2])}, +{len(selected_types) - 2} more")
            else:
                st.caption("All")

        with col4:
            st.metric("Positions", len(filtered_symbols))
            if len(filtered_symbols) <= 5:
                st.caption(", ".join(filtered_symbols))
            else:
                st.caption(f"{', '.join(filtered_symbols[:3])}, +{len(filtered_symbols) - 3} more")

        if len(date_range) == 2 and date_range[0] and date_range[1]:
            days = (date_range[1] - date_range[0]).days + 1
            st.caption(
                f"{StockTrackerConfig.FILTER_DATE_RANGE_LABEL}: "
                f"{date_range[0]} to {date_range[1]} ({days} days)"
            )
        else:
            st.caption(StockTrackerConfig.FILTER_DATE_RANGE_ALL)


def show_stock_tracker(
    trading_log: pd.DataFrame,
    historical: pd.DataFrame,
) -> None:
    """Render the Stock Tracker view with filtering and analytics."""
    try:
        st.title(StockTrackerConfig.TITLE)

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

        required_columns = {
            StockColumnNames.DATE.lower(): StockColumnNames.DATE,
            StockColumnNames.TICKER.lower(): "ticker (or Symbol)",
            StockColumnNames.QUANTITY.lower(): StockColumnNames.QUANTITY,
            StockColumnNames.BROKERAGE.lower(): StockColumnNames.BROKERAGE,
            StockColumnNames.ACCOUNT_NAME.lower(): StockColumnNames.ACCOUNT_NAME,
            StockColumnNames.INVESTMENT_TYPE.lower(): StockColumnNames.INVESTMENT_TYPE,
        }

        col_mapping = {col.lower(): col for col in historical.columns}

        missing = []
        for req_col_lower, req_col_display in required_columns.items():
            if req_col_lower == StockColumnNames.TICKER.lower():
                if (
                    StockColumnNames.TICKER.lower() not in col_mapping
                    and StockColumnNames.SYMBOL.lower() not in col_mapping
                ):
                    missing.append(req_col_display)
            elif req_col_lower not in col_mapping:
                missing.append(req_col_display)

        if missing:
            st.error(
                f"Historical tracking data is missing required columns: {', '.join(missing)}"
            )
            st.info(
                "Please add these columns to your Historical_Tracking sheet: "
                "Brokerage, Account Name, Investment Type"
            )
            with st.expander(StockTrackerConfig.AVAILABLE_COLUMNS_TITLE):
                st.write(list(historical.columns))
            return

        selected_brokerages, selected_accounts, selected_types = render_stock_header_filters(
            historical
        )

        if not selected_brokerages and not selected_accounts and not selected_types:
            st.info("Please select at least one brokerage, account, or investment type to view portfolio data.")
            return

        date_range = render_stock_sidebar_filters(
            historical,
            selected_brokerages,
            selected_accounts,
            selected_types,
        )

        historical_filtered = _filter_by_header_selections(
            historical,
            selected_brokerages,
            selected_accounts,
            selected_types,
        )

        if historical_filtered.empty:
            st.warning("No data available for the selected brokerages, accounts, and investment types.")
            return

        historical_filtered = _filter_by_date_range(historical_filtered, date_range)

        if historical_filtered.empty:
            st.warning("No data available for the selected date range.")
            return

        filtered_symbols = _get_filtered_symbols(historical_filtered)

        if not filtered_symbols:
            st.info("No currently owned positions found for the selected filters.")
            return

        if trading_log is not None and not trading_log.empty:
            try:
                trading_log_filtered = trading_log[
                    trading_log[StockColumnNames.TICKER].isin(filtered_symbols)
                ].copy()
            except Exception:
                trading_log_filtered = pd.DataFrame()
        else:
            trading_log_filtered = pd.DataFrame()

        _display_filter_summary(
            selected_brokerages,
            selected_accounts,
            selected_types,
            filtered_symbols,
            date_range,
        )

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(StockTrackerConfig.TAB_NAMES)

        with tab1:
            overview.render(historical_filtered, filtered_symbols, trading_log_filtered)

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
        with st.expander(StockTrackerConfig.ERROR_DETAILS_TITLE):
            st.exception(e)
