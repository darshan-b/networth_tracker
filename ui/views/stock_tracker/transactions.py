"""Transactions tab for portfolio analysis.

This module provides transaction history visualization and analysis.
"""

from typing import Optional

import streamlit as st
import pandas as pd

from ui.charts import create_transaction_timeline
from ui.components.surfaces import inject_surface_styles, render_accent_pills, render_section_intro

DIVIDEND_TYPE_TOKENS = ("dividend", "distribution")


def render(trading_log_df: pd.DataFrame, historical_df: Optional[pd.DataFrame] = None) -> None:
    """Render the transaction history tab.

    Args:
        trading_log_df: Trading log DataFrame (already filtered by accounts)
        historical_df: Historical tracking DataFrame for current price lookups
    """
    try:
        inject_surface_styles()
        st.header("Transaction History")

        if trading_log_df is None or trading_log_df.empty:
            st.info("No transaction data available for selected filters.")
            return

        trading_log_df = trading_log_df.copy()

        render_section_intro(
            "Cash Flow",
            "Review buys, sells, and dividend income for the current stock-tracker filter set.",
        )
        _render_transaction_summary(trading_log_df)

        render_section_intro(
            "Dividends",
            "See dividend cash, reinvested share quantity, and the current value of those shares by holding.",
        )
        _render_dividend_summary(trading_log_df, historical_df)

        render_section_intro(
            "Timeline",
            "Compare transaction activity over time across the selected holdings.",
        )
        _render_transaction_timeline(trading_log_df)

        render_section_intro(
            "Transaction Mix",
            "Break down trading-log activity by transaction type.",
        )
        _render_transaction_breakdown(trading_log_df)

        render_section_intro(
            "Recent Activity",
            "Inspect the latest entries before drilling into the full transaction ledger.",
        )
        _render_recent_transactions(trading_log_df)

        render_section_intro(
            "All Transactions",
            "Filter the full ledger by type, symbol, and sort order.",
        )
        _render_all_transactions(trading_log_df)

    except Exception as e:
        st.error(f"Error rendering transaction history: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _get_dividend_rows(df: pd.DataFrame) -> pd.DataFrame:
    if 'Transaction Type' not in df.columns:
        return df.iloc[0:0].copy()

    type_series = df['Transaction Type'].fillna('').astype(str)
    mask = type_series.str.lower().apply(
        lambda value: any(token in value for token in DIVIDEND_TYPE_TOKENS)
    )
    return df[mask].copy()


def _get_group_columns(df: pd.DataFrame) -> list[str]:
    return [
        column for column in ['Brokerage', 'Account Name', 'ticker']
        if column in df.columns
    ]


def _get_latest_price_map(historical_df: Optional[pd.DataFrame]) -> pd.Series:
    if historical_df is None or historical_df.empty:
        return pd.Series(dtype=float)
    required = {'Date', 'ticker', 'Last Close'}
    if not required.issubset(historical_df.columns):
        return pd.Series(dtype=float)

    latest_prices = (
        historical_df[['Date', 'ticker', 'Last Close']]
        .dropna(subset=['ticker', 'Last Close'])
        .sort_values('Date')
        .groupby('ticker')
        .last()['Last Close']
    )
    return latest_prices


def _render_transaction_summary(df: pd.DataFrame) -> None:
    total_transactions = len(df)

    buys = df[df['Transaction Type'] == 'Buy'] if 'Transaction Type' in df.columns else df.iloc[0:0]
    sells = df[df['Transaction Type'] == 'Sell'] if 'Transaction Type' in df.columns else df.iloc[0:0]
    dividends = _get_dividend_rows(df)

    total_invested = buys['Amount'].sum() if 'Amount' in buys.columns else 0.0
    total_proceeds = sells['Amount'].sum() if 'Amount' in sells.columns else 0.0
    total_dividends = dividends['Amount'].sum() if 'Amount' in dividends.columns else 0.0
    dividend_symbols = dividends['ticker'].nunique() if 'ticker' in dividends.columns else 0

    cols = st.columns(5)
    with cols[0]:
        st.metric("Total Transactions", total_transactions)
    with cols[1]:
        st.metric("Total Invested", f"${total_invested:,.2f}")
    with cols[2]:
        st.metric("Total Proceeds", f"${total_proceeds:,.2f}")
    with cols[3]:
        st.metric("Total Dividends", f"${total_dividends:,.2f}")
    with cols[4]:
        net_flow = total_invested - total_proceeds
        st.metric("Net Flow", f"${net_flow:,.2f}")

    render_accent_pills([
        ("Dividend rows", f"{len(dividends):,}"),
        ("Dividend symbols", f"{dividend_symbols:,}"),
    ])
    st.divider()


def _render_dividend_summary(df: pd.DataFrame, historical_df: Optional[pd.DataFrame]) -> None:
    dividend_df = _get_dividend_rows(df)
    if dividend_df.empty:
        st.caption("No dividend or distribution transactions were found for the selected filters.")
        return

    latest_price_map = _get_latest_price_map(historical_df)
    dividend_df = dividend_df.copy()
    if 'ticker' in dividend_df.columns and not latest_price_map.empty:
        dividend_df['Current Price'] = dividend_df['ticker'].map(latest_price_map)
    else:
        dividend_df['Current Price'] = pd.NA

    if 'Quantity' in dividend_df.columns:
        dividend_df['Current Dividend Share Value'] = (
            dividend_df['Quantity'].fillna(0) * dividend_df['Current Price'].fillna(0)
        )
        total_dividend_quantity = dividend_df['Quantity'].sum()
    else:
        dividend_df['Current Dividend Share Value'] = 0.0
        total_dividend_quantity = 0.0

    total_dividend_value = dividend_df['Amount'].sum() if 'Amount' in dividend_df.columns else 0.0
    total_current_share_value = dividend_df['Current Dividend Share Value'].sum()
    unique_positions = dividend_df[_get_group_columns(dividend_df)].drop_duplicates().shape[0]

    cols = st.columns(4)
    with cols[0]:
        st.metric("Dividend Value", f"${total_dividend_value:,.2f}")
    with cols[1]:
        st.metric("Dividend Quantity", f"{total_dividend_quantity:,.4f}")
    with cols[2]:
        st.metric("Dividend Shares Now Worth", f"${total_current_share_value:,.2f}")
    with cols[3]:
        st.metric("Positions Paid", unique_positions)

    group_columns = _get_group_columns(dividend_df)
    aggregation = {'Amount': 'sum', 'Current Dividend Share Value': 'sum'}
    if 'Quantity' in dividend_df.columns:
        aggregation['Quantity'] = 'sum'
    if 'Date' in dividend_df.columns:
        aggregation['Date'] = 'max'
    aggregation['Transaction Type'] = 'count'

    dividend_summary = (
        dividend_df.groupby(group_columns, dropna=False)
        .agg(aggregation)
        .reset_index()
    )

    dividend_summary = dividend_summary.rename(columns={
        'Amount': 'Dividend Value',
        'Quantity': 'Dividend Quantity',
        'Current Dividend Share Value': 'Dividend Shares Now Worth',
        'Date': 'Latest Dividend',
        'Transaction Type': 'Dividend Rows',
    })

    dividend_summary = dividend_summary.sort_values('Dividend Value', ascending=False)

    format_dict = {
        'Dividend Value': '${:,.2f}',
        'Dividend Shares Now Worth': '${:,.2f}',
        'Dividend Rows': '{:.0f}',
    }
    if 'Dividend Quantity' in dividend_summary.columns:
        format_dict['Dividend Quantity'] = '{:.4f}'

    st.dataframe(
        dividend_summary.style.format(format_dict),
        width='stretch',
        hide_index=True,
        height=min(420, 44 + 35 * len(dividend_summary))
    )


def _render_transaction_timeline(df: pd.DataFrame) -> None:
    try:
        if 'Date' not in df.columns:
            st.warning("Date information not available for timeline.")
            return

        fig = create_transaction_timeline(df)
        st.plotly_chart(fig, config={"responsive": True})
    except Exception as e:
        st.error(f"Error creating timeline chart: {str(e)}")


def _render_transaction_breakdown(df: pd.DataFrame) -> None:
    if 'Transaction Type' not in df.columns:
        st.warning("Transaction type information not available.")
        return

    aggregation = {'Amount': ['sum', 'count', 'mean']}
    if 'Quantity' in df.columns:
        aggregation['Quantity'] = 'sum'

    trans_summary = df.groupby('Transaction Type').agg(aggregation).reset_index()

    columns = ['Transaction Type', 'Total Amount', 'Count', 'Avg Amount']
    if 'Quantity' in df.columns:
        columns.append('Total Quantity')
    trans_summary.columns = columns

    format_dict = {
        'Total Amount': '${:,.2f}',
        'Count': '{:.0f}',
        'Avg Amount': '${:,.2f}',
    }
    if 'Total Quantity' in trans_summary.columns:
        format_dict['Total Quantity'] = '{:.4f}'

    st.dataframe(
        trans_summary.style.format(format_dict),
        width="stretch",
        hide_index=True
    )


def _render_recent_transactions(df: pd.DataFrame, n: int = 20) -> None:
    if 'Date' not in df.columns:
        st.warning("Date information not available.")
        return

    recent = df.sort_values('Date', ascending=False).head(n)

    display_columns = []
    for col in ['Date', 'Brokerage', 'Account Name', 'ticker', 'Transaction Type', 'Quantity', 'Amount']:
        if col in recent.columns:
            display_columns.append(col)

    if not display_columns:
        st.warning("No transaction data to display.")
        return

    recent_display = recent[display_columns].copy()

    format_dict = {}
    if 'Quantity' in recent_display.columns:
        format_dict['Quantity'] = '{:.4f}'
    if 'Amount' in recent_display.columns:
        format_dict['Amount'] = '${:,.2f}'

    st.dataframe(
        recent_display.style.format(format_dict),
        width="stretch",
        hide_index=True,
        height=400
    )


def _render_all_transactions(df: pd.DataFrame) -> None:
    col1, col2, col3 = st.columns(3)

    filtered_df = df.copy()

    if 'Transaction Type' in df.columns:
        with col1:
            trans_types = ['All'] + sorted(df['Transaction Type'].dropna().astype(str).unique().tolist())
            selected_type = st.selectbox(
                "Transaction Type",
                trans_types,
                key='trans_type_filter'
            )

            if selected_type != 'All':
                filtered_df = filtered_df[
                    filtered_df['Transaction Type'] == selected_type
                ]

    if 'ticker' in df.columns:
        with col2:
            symbols = ['All'] + sorted(df['ticker'].dropna().astype(str).unique().tolist())
            selected_symbol = st.selectbox(
                "Symbol",
                symbols,
                key='symbol_filter'
            )

            if selected_symbol != 'All':
                filtered_df = filtered_df[filtered_df['ticker'] == selected_symbol]

    with col3:
        sort_order = st.selectbox(
            "Sort By",
            ['Date (Newest)', 'Date (Oldest)', 'Amount (Highest)', 'Amount (Lowest)'],
            key='sort_order'
        )

    if 'Date' in filtered_df.columns:
        if sort_order == 'Date (Newest)':
            filtered_df = filtered_df.sort_values('Date', ascending=False)
        elif sort_order == 'Date (Oldest)':
            filtered_df = filtered_df.sort_values('Date', ascending=True)

    if 'Amount' in filtered_df.columns:
        if sort_order == 'Amount (Highest)':
            filtered_df = filtered_df.sort_values('Amount', ascending=False)
        elif sort_order == 'Amount (Lowest)':
            filtered_df = filtered_df.sort_values('Amount', ascending=True)

    st.caption(f"Showing {len(filtered_df)} of {len(df)} transactions")

    display_columns = []
    for col in ['Date', 'Brokerage', 'Account Name', 'ticker', 'Transaction Type', 'Quantity', 'Amount', 'Price']:
        if col in filtered_df.columns:
            display_columns.append(col)

    if display_columns:
        display_df = filtered_df[display_columns].copy()

        format_dict = {}
        if 'Quantity' in display_df.columns:
            format_dict['Quantity'] = '{:.4f}'
        if 'Amount' in display_df.columns:
            format_dict['Amount'] = '${:,.2f}'
        if 'Price' in display_df.columns:
            format_dict['Price'] = '${:.2f}'

        st.dataframe(
            display_df.style.format(format_dict),
            width="stretch",
            hide_index=True,
            height=500
        )
    else:
        st.warning("No transaction data to display.")
