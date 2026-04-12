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
from ui.components.utils import render_tabs_safely
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

    if StockColumnNames.DATE not in df.columns:
        return df

    start_date, end_date = date_range
    return df[
        (df[StockColumnNames.DATE].dt.date >= start_date)
        & (df[StockColumnNames.DATE].dt.date <= end_date)
    ].copy()


def _get_filtered_symbols(historical_df: pd.DataFrame) -> List[str]:
    """Get list of currently owned symbols from historical data."""
    required_columns = [
        StockColumnNames.DATE,
        StockColumnNames.TICKER,
        StockColumnNames.QUANTITY,
    ]
    if any(col not in historical_df.columns for col in required_columns):
        return []

    try:
        latest_data = (
            historical_df
            .sort_values(StockColumnNames.DATE)
            .groupby(StockColumnNames.TICKER)
            .last()
            .reset_index()
        )
        currently_owned = latest_data[
            latest_data[StockColumnNames.QUANTITY] > 0
        ][StockColumnNames.TICKER].unique().tolist()
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
            StockColumnNames.DATE: StockColumnNames.DATE,
            StockColumnNames.TICKER: "ticker",
            StockColumnNames.QUANTITY: StockColumnNames.QUANTITY,
            StockColumnNames.BROKERAGE: StockColumnNames.BROKERAGE,
            StockColumnNames.ACCOUNT_NAME: StockColumnNames.ACCOUNT_NAME,
            StockColumnNames.INVESTMENT_TYPE: StockColumnNames.INVESTMENT_TYPE,
        }
        missing = [label for column, label in required_columns.items() if column not in historical.columns]

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

        tab_configs = [
            {
                'render_func': overview.render,
                'args': [historical_filtered, filtered_symbols, trading_log_filtered],
                'context': 'overview',
            },
            {
                'render_func': performance.render,
                'args': [historical_filtered, filtered_symbols],
                'context': 'performance',
            },
            {
                'render_func': allocation.render,
                'args': [historical_filtered],
                'context': 'allocation',
            },
            {
                'render_func': risk_analysis.render,
                'args': [historical_filtered, filtered_symbols],
                'context': 'risk analysis',
            },
            {
                'render_func': transactions.render,
                'args': [trading_log_filtered],
                'context': 'transactions',
            },
            {
                'render_func': cost_basis.render,
                'args': [historical_filtered],
                'context': 'cost basis',
            },
        ]

        render_tabs_safely(tab_configs, StockTrackerConfig.TAB_NAMES)

    except Exception as e:
        st.error(f"An error occurred while loading the Stock Tracker: {str(e)}")
        with st.expander(StockTrackerConfig.ERROR_DETAILS_TITLE):
            st.exception(e)
