"""Stock Tracker view module."""

from datetime import datetime
from typing import List, Tuple

import pandas as pd
import streamlit as st

from config import StockTrackerConfig
from app_constants import StockColumnNames
from data.stock_analytics import (
    build_position_key,
    get_active_position_keys,
    get_active_latest_positions,
    get_filtered_symbols,
)
from ui.components.utils import render_empty_state, render_tabs_safely
from ui.components.filters import render_stock_header_filters, render_stock_sidebar_filters
from ui.components.surfaces import inject_surface_styles, render_accent_pills, render_section_intro
from ui.views.stock_tracker import (
    allocation,
    cost_basis,
    overview,
    performance,
    risk_analysis,
    transactions,
)
def _normalize_key_series(series: pd.Series) -> pd.Series:
    """Normalize label fields so filters and joins survive spacing/case drift."""
    return series.fillna("").astype(str).str.strip().str.casefold()


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
        selected = {_normalize_key_series(pd.Series(selected_brokerages)).iloc[i] for i in range(len(selected_brokerages))}
        conditions.append(_normalize_key_series(df[StockColumnNames.BROKERAGE]).isin(selected))

    if selected_accounts and StockColumnNames.ACCOUNT_NAME in df.columns:
        selected = {_normalize_key_series(pd.Series(selected_accounts)).iloc[i] for i in range(len(selected_accounts))}
        conditions.append(_normalize_key_series(df[StockColumnNames.ACCOUNT_NAME]).isin(selected))

    if selected_types and StockColumnNames.INVESTMENT_TYPE in df.columns:
        selected = {_normalize_key_series(pd.Series(selected_types)).iloc[i] for i in range(len(selected_types))}
        conditions.append(_normalize_key_series(df[StockColumnNames.INVESTMENT_TYPE]).isin(selected))

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
        StockColumnNames.BROKERAGE,
        StockColumnNames.ACCOUNT_NAME,
    ]
    if any(col not in historical_df.columns for col in required_columns):
        return []

    try:
        return get_filtered_symbols(historical_df)
    except Exception:
        return []


def _get_position_count(historical_df: pd.DataFrame) -> int:
    """Get currently owned position count from historical data."""
    required_columns = [
        StockColumnNames.DATE,
        StockColumnNames.TICKER,
        StockColumnNames.QUANTITY,
        StockColumnNames.BROKERAGE,
        StockColumnNames.ACCOUNT_NAME,
    ]
    if any(col not in historical_df.columns for col in required_columns):
        return 0

    try:
        return int(len(get_active_latest_positions(historical_df)))
    except Exception:
        return 0


def _get_active_position_keys(historical_df: pd.DataFrame) -> list[str]:
    """Return active brokerage/account/ticker keys from filtered historical data."""
    required_columns = [
        StockColumnNames.DATE,
        StockColumnNames.TICKER,
        StockColumnNames.QUANTITY,
        StockColumnNames.BROKERAGE,
        StockColumnNames.ACCOUNT_NAME,
    ]
    if any(col not in historical_df.columns for col in required_columns):
        return []

    try:
        return get_active_position_keys(historical_df)
    except Exception:
        return []


def _filter_trading_log_to_active_positions(
    trading_log_df: pd.DataFrame,
    active_position_keys: list[str],
) -> pd.DataFrame:
    """Keep only rows matching active brokerage/account/ticker positions."""
    if trading_log_df is None or trading_log_df.empty or not active_position_keys:
        return pd.DataFrame()

    required_columns = [
        StockColumnNames.BROKERAGE,
        StockColumnNames.ACCOUNT_NAME,
        StockColumnNames.TICKER,
    ]
    if any(col not in trading_log_df.columns for col in required_columns):
        return trading_log_df.copy()

    filtered = trading_log_df.copy()
    filtered["_position_key"] = build_position_key(filtered)
    filtered = filtered[filtered["_position_key"].isin(active_position_keys)].copy()
    return filtered.drop(columns=["_position_key"], errors='ignore')


def _display_filter_summary(
    selected_brokerages: List[str],
    selected_accounts: List[str],
    selected_types: List[str],
    filtered_symbols: List[str],
    position_count: int,
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
            st.metric("Positions", position_count)
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


def _render_stock_tracker_summary(
    historical_filtered: pd.DataFrame,
    trading_log_filtered: pd.DataFrame,
    filtered_symbols: List[str],
    position_count: int,
    date_range: Tuple[datetime, datetime],
) -> None:
    """Render a cohesive Stock Tracker summary surface like the other main products."""
    if historical_filtered.empty:
        return

    latest_date = pd.to_datetime(historical_filtered[StockColumnNames.DATE]).max()
    latest_label = latest_date.strftime("%b %d, %Y") if pd.notna(latest_date) else "N/A"
    brokerages = historical_filtered[StockColumnNames.BROKERAGE].nunique()
    accounts = historical_filtered[StockColumnNames.ACCOUNT_NAME].nunique()
    types = historical_filtered[StockColumnNames.INVESTMENT_TYPE].nunique()
    trade_count = len(trading_log_filtered) if trading_log_filtered is not None else 0

    render_section_intro(
        "Stock Tracker",
        "Move from the latest holdings snapshot into overview, performance, allocation, risk, transactions, and cost basis without losing brokerage/account context.",
    )

    pills = [
        ("Latest Snapshot", latest_label),
        ("Brokerages", str(brokerages)),
        ("Accounts", str(accounts)),
        ("Types", str(types)),
        ("Positions", str(position_count)),
        ("Symbols", str(len(filtered_symbols))),
    ]
    if trade_count:
        pills.append(("Transactions", f"{trade_count:,}"))
    if len(date_range) == 2 and date_range[0] and date_range[1]:
        pills.append(("Range", f"{date_range[0]} to {date_range[1]}"))
    render_accent_pills(pills)
    st.divider()


def show_stock_tracker(
    trading_log: pd.DataFrame,
    historical: pd.DataFrame,
) -> None:
    """Render the Stock Tracker view with filtering and analytics."""
    try:
        inject_surface_styles()

        if historical is None or historical.empty:
            render_empty_state(
                title="No Historical Tracking Data",
                message=(
                    "Historical tracking data not found. Please ensure your "
                    "`Historical_Tracking` sheet has data."
                ),
                show_tips=True,
                tips=[
                    "Run `historical_stock_tracking.py` to rebuild the sheet.",
                    "Verify the workbook includes `Date`, `ticker`, `quantity`, `Brokerage`, `Account Name`, and `Investment Type`.",
                    "Check the selected filters and date range.",
                ],
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
            render_empty_state(
                title="Historical Tracking Columns Missing",
                message=(
                    f"Historical tracking data is missing required columns: {', '.join(missing)}"
                ),
                show_tips=True,
                tips=[
                    "Rebuild `Historical_Tracking` from the latest script.",
                    "Ensure the sheet includes Brokerage, Account Name, and Investment Type.",
                    "Open the available-columns expander below to compare the loaded schema.",
                ],
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
        position_count = _get_position_count(historical_filtered)
        active_position_keys = _get_active_position_keys(historical_filtered)

        if not filtered_symbols:
            st.info("No currently owned positions found for the selected filters.")
            return

        if trading_log is not None and not trading_log.empty:
            try:
                trading_log_filtered = _filter_by_header_selections(
                    trading_log,
                    selected_brokerages,
                    selected_accounts,
                    selected_types,
                )
                trading_log_filtered = _filter_trading_log_to_active_positions(
                    trading_log_filtered,
                    active_position_keys,
                )
            except Exception:
                trading_log_filtered = pd.DataFrame()
        else:
            trading_log_filtered = pd.DataFrame()

        _render_stock_tracker_summary(
            historical_filtered,
            trading_log_filtered,
            filtered_symbols,
            position_count,
            date_range,
        )
        _display_filter_summary(
            selected_brokerages,
            selected_accounts,
            selected_types,
            filtered_symbols,
            position_count,
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
                'args': [trading_log_filtered, historical_filtered],
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
