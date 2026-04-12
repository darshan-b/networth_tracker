"""Overview dashboard for the Net Worth Tracker."""

import pandas as pd
import streamlit as st

from config import ChartConfig
from constants import ColumnNames
from data.calculations import calculate_metrics
from ui.charts import (
    create_donut_chart,
    create_horizontal_bar_chart,
    create_top_accounts_chart,
)
from ui.components.utils import render_metric_cards


def _format_currency(value: float) -> str:
    """Format currency values consistently for overview cards."""
    return f"${value:,.0f}"


def _format_delta(value: float, pct_value: float) -> str:
    """Format absolute and percentage period change together."""
    return f"{value:+,.0f} ({pct_value:+.2f}%)"


def _build_overview_highlights(
    latest_month_label: str,
    metrics: dict,
    previous_month_exists: bool,
) -> list[dict[str, str]]:
    """Create compact narrative highlights for the overview header."""
    liability_share = (
        metrics["current_liabilities"] / metrics["current_assets"] * 100
        if metrics["current_assets"] > 0
        else 0
    )

    momentum_text = "No prior period available yet."
    if previous_month_exists:
        if metrics["net_worth_change"] > 0:
            momentum_text = (
                f"Net worth increased by {_format_currency(abs(metrics['net_worth_change']))} "
                f"since the previous snapshot."
            )
        elif metrics["net_worth_change"] < 0:
            momentum_text = (
                f"Net worth decreased by {_format_currency(abs(metrics['net_worth_change']))} "
                f"since the previous snapshot."
            )
        else:
            momentum_text = "Net worth was flat versus the previous snapshot."

    return [
        {
            "label": "Latest Snapshot",
            "value": latest_month_label,
            "caption": "Most recent month available in the filtered dataset.",
        },
        {
            "label": "Balance Mix",
            "value": f"{liability_share:.1f}% debt share",
            "caption": "Liabilities as a share of current assets.",
        },
        {
            "label": "Momentum",
            "value": "Moving Up" if metrics["net_worth_change"] > 0 else "Stable" if metrics["net_worth_change"] == 0 else "Cooling Off",
            "caption": momentum_text,
        },
    ]


def _render_highlight_strip(highlights: list[dict[str, str]]) -> None:
    """Render a lightweight narrative strip above the main charts."""
    columns = st.columns(len(highlights))
    for column, highlight in zip(columns, highlights):
        with column:
            st.caption(highlight["label"])
            st.markdown(f"**{highlight['value']}**")
            st.caption(highlight["caption"])


def render_dashboard(filtered_df: pd.DataFrame) -> None:
    """Render the overview dashboard for net worth analysis."""
    latest_month = filtered_df[ColumnNames.MONTH].max()
    latest_month_rows = filtered_df[filtered_df[ColumnNames.MONTH] == latest_month]
    latest_month_label = latest_month_rows[ColumnNames.MONTH_STR].iloc[0]

    unique_months = filtered_df[ColumnNames.MONTH].drop_duplicates().sort_values().tolist()
    previous_month = unique_months[-2] if len(unique_months) > 1 else None
    previous_data = (
        filtered_df[filtered_df[ColumnNames.MONTH] == previous_month]
        if previous_month is not None
        else pd.DataFrame()
    )

    metrics = calculate_metrics(latest_month_rows, previous_data)
    previous_month_exists = not previous_data.empty

    st.subheader("Net Worth Overview")
    st.caption(
        "A calmer snapshot of your current position, what changed recently, and how your balances are distributed."
    )

    metrics_config = {
        "net_worth": {
            "label": "Net Worth",
            "value": _format_currency(metrics["current_net_worth"]),
            "delta": (
                _format_delta(
                    metrics["net_worth_change"],
                    metrics["net_worth_pct_change"],
                )
                if previous_month_exists
                else None
            ),
        },
        "assets": {
            "label": "Total Assets",
            "value": _format_currency(metrics["current_assets"]),
        },
        "liabilities": {
            "label": "Total Liabilities",
            "value": _format_currency(metrics["current_liabilities"]),
            "delta": (
                f"{metrics['liabilities_change_pct']:+.2f}%"
                if previous_month_exists
                else None
            ),
            "delta_color": "inverse",
        },
        "debt_ratio": {
            "label": "Debt Ratio",
            "value": f"{metrics['debt_ratio']:.1f}%",
        },
    }
    render_metric_cards(metrics_config, num_columns=4)

    st.markdown("")
    _render_highlight_strip(
        _build_overview_highlights(
            latest_month_label=latest_month_label,
            metrics=metrics,
            previous_month_exists=previous_month_exists,
        )
    )

    st.divider()
    st.markdown("### Where Your Balance Sits")
    st.caption("The left chart focuses on positive holdings. The right side shows debt pressure if liabilities exist.")

    holdings_col, liabilities_col = st.columns(2)

    holdings_data = latest_month_rows[
        latest_month_rows[ColumnNames.ACCOUNT_TYPE] != "Liability"
    ]
    holdings_by_category = (
        holdings_data.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .sort_values(ascending=False)
    )

    with holdings_col:
        st.markdown("**Holdings by Category**")
        fig_holdings = create_horizontal_bar_chart(
            holdings_by_category,
            "Holdings by Category",
            "assets",
            metrics["current_assets"],
        )
        st.plotly_chart(fig_holdings, config=ChartConfig.STREAMLIT_CONFIG)

    with liabilities_col:
        st.markdown("**Liabilities by Category**")
        liability_data = latest_month_rows[
            latest_month_rows[ColumnNames.ACCOUNT_TYPE] == "Liability"
        ]

        if liability_data.empty:
            st.caption("No liabilities are recorded for the latest snapshot.")
            st.metric(
                "Liability Balance",
                _format_currency(0),
                border=True,
            )
        else:
            liability_by_category = (
                liability_data.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
                .sum()
                .abs()
                .sort_values(ascending=False)
            )
            fig_liabilities = create_horizontal_bar_chart(
                liability_by_category,
                "Liabilities by Category",
                "liabilities",
                metrics["current_liabilities"],
            )
            st.plotly_chart(fig_liabilities, config=ChartConfig.STREAMLIT_CONFIG)

    st.divider()
    st.markdown("### Composition At A Glance")
    st.caption("A quick read on how your finances are distributed across account types and your largest balances.")

    composition_col, top_accounts_col = st.columns(2)

    with composition_col:
        st.markdown("**Account Type Mix**")
        account_type_dist = latest_month_rows.copy()
        account_type_dist["display_amount"] = account_type_dist[ColumnNames.AMOUNT].abs()
        account_type_dist = account_type_dist.groupby(ColumnNames.ACCOUNT_TYPE)["display_amount"].sum()

        fig_type = create_donut_chart(account_type_dist, "Account Type Mix")
        st.plotly_chart(fig_type, config=ChartConfig.STREAMLIT_CONFIG)

    with top_accounts_col:
        st.markdown("**Largest Accounts**")
        top_accounts = latest_month_rows.copy()
        top_accounts[ColumnNames.AMOUNT] = top_accounts[ColumnNames.AMOUNT].abs()
        top_accounts = top_accounts.nlargest(
            5,
            ColumnNames.AMOUNT,
        )[[ColumnNames.ACCOUNT, ColumnNames.AMOUNT, ColumnNames.CATEGORY]]

        fig_top = create_top_accounts_chart(top_accounts)
        fig_top.update_layout(title="Largest Accounts")
        st.plotly_chart(fig_top, config=ChartConfig.STREAMLIT_CONFIG)
