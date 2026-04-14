"""Allocation tab for portfolio analysis.

This module provides asset allocation visualization and gain/loss analysis.
"""

import streamlit as st
import pandas as pd

from config import ChartConfig
from ui.charts import create_allocation_chart, create_gain_loss_chart
from ui.components.surfaces import inject_surface_styles, render_accent_pills, render_section_intro


def _build_position_key(df: pd.DataFrame) -> pd.Series:
    """Build a stable position key to keep same-ticker holdings separate before aggregation."""
    return (
        df['Brokerage'].astype(str)
        + '||' + df['Account Name'].astype(str)
        + '||' + df['ticker'].astype(str)
    )


def _aggregate_latest_holdings(historical_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate active latest holdings to ticker-level allocation view."""
    latest_data = historical_df.copy()
    latest_data['position_key'] = _build_position_key(latest_data)
    latest_data = (
        latest_data
        .sort_values('Date')
        .groupby('position_key')
        .last()
        .reset_index()
    )
    latest_data = latest_data[latest_data['quantity'] > 0].copy()
    if latest_data.empty:
        return latest_data

    aggregation = {
        'quantity': 'sum',
        'Cost Basis': 'sum',
        'Current Value': 'sum',
        'Total Gain/Loss': 'sum',
    }
    if 'Investment Type' in latest_data.columns:
        aggregation['Investment Type'] = 'first'
    if 'Date' in latest_data.columns:
        aggregation['Date'] = 'max'

    aggregated = (
        latest_data.groupby('ticker', as_index=False)
        .agg(aggregation)
    )
    aggregated['Total Gain/Loss %'] = aggregated.apply(
        lambda row: (row['Total Gain/Loss'] / row['Cost Basis'] * 100)
        if row['Cost Basis'] else 0.0,
        axis=1,
    )
    return aggregated


def render(historical_df: pd.DataFrame) -> None:
    """Render the portfolio allocation tab.

    Args:
        historical_df: Historical tracking DataFrame (already filtered)
    """
    try:
        inject_surface_styles()
        render_section_intro(
            "Portfolio Allocation",
            "See how the filtered portfolio is distributed across tickers, with same-symbol holdings combined across brokerages and accounts.",
        )

        if historical_df.empty:
            st.warning("No historical tracking data available for selected filters.")
            return

        latest_data = _aggregate_latest_holdings(historical_df)

        if latest_data.empty:
            st.info("No currently owned positions found for selected filters.")
            return

        _render_allocation_summary(latest_data)

        col1, col2 = st.columns(2)

        with col1:
            _render_allocation_pie(latest_data)

        with col2:
            _render_gain_loss_bar(latest_data)

        render_section_intro(
            "Allocation Details",
            "Ticker-level breakdown of value, allocation share, and gain/loss for the filtered holdings.",
        )
        _render_allocation_table(latest_data)

    except Exception as e:
        st.error(f"Error rendering allocation analysis: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_allocation_summary(data: pd.DataFrame) -> None:
    """Render summary metrics for allocation.

    Args:
        data: Latest ticker-level data
    """
    total_value = data['Current Value'].sum()
    total_positions = len(data)
    avg_position_size = total_value / total_positions if total_positions > 0 else 0

    largest = data.loc[data['Current Value'].idxmax()]
    largest_pct = (largest['Current Value'] / total_value * 100) if total_value > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Holdings", total_positions)

    with col2:
        st.metric("Avg Holding Size", f"${avg_position_size:,.2f}")

    with col3:
        st.metric("Largest Holding", largest['ticker'])

    with col4:
        st.metric("Largest %", f"{largest_pct:.1f}%")

    st.divider()


def _render_allocation_pie(data: pd.DataFrame) -> None:
    """Render allocation pie chart."""
    try:
        fig = create_allocation_chart(data)
        st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)
    except Exception as e:
        st.error(f"Error creating allocation chart: {str(e)}")


def _render_gain_loss_bar(data: pd.DataFrame) -> None:
    """Render gain/loss bar chart."""
    try:
        fig = create_gain_loss_chart(data)
        st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)
    except Exception as e:
        st.error(f"Error creating gain/loss chart: {str(e)}")


def _render_allocation_table(data: pd.DataFrame) -> None:
    """Render detailed allocation table."""
    table_data = data.copy()

    total_value = table_data['Current Value'].sum()
    table_data['Allocation %'] = (
        (table_data['Current Value'] / total_value * 100)
        if total_value > 0 else 0
    )

    display_columns = ['ticker']
    if 'Investment Type' in table_data.columns:
        display_columns.append('Investment Type')
    display_columns.extend([
        'quantity',
        'Current Value',
        'Allocation %',
        'Total Gain/Loss',
        'Total Gain/Loss %'
    ])

    table_data = table_data[display_columns].copy()
    table_data = table_data.rename(columns={
        'ticker': 'Ticker',
        'quantity': 'Quantity',
        'Current Value': 'Value',
        'Allocation %': 'Allocation %',
        'Total Gain/Loss': 'Gain/Loss ($)',
        'Total Gain/Loss %': 'Gain/Loss (%)',
    })

    table_data = table_data.sort_values('Allocation %', ascending=False)

    format_dict = {
        'Quantity': '{:.3f}',
        'Value': '${:,.2f}',
        'Allocation %': '{:.2f}%',
        'Gain/Loss ($)': '${:,.2f}',
        'Gain/Loss (%)': '{:.2f}%'
    }

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
        width="stretch",
        height=400
    )

    render_accent_pills(
        [
            ("Top 3 Share", f"{table_data.head(3)['Allocation %'].sum():.1f}%"),
            ("Holdings", str(len(table_data))),
            ("Investment Types", str(data['Investment Type'].nunique()) if 'Investment Type' in data.columns else "N/A"),
        ]
    )
