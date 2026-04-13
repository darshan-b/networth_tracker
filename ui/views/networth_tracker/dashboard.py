"""Overview dashboard for the Net Worth Tracker."""

import pandas as pd
import streamlit as st

from config import ChartConfig, NetWorthOverviewConfig
from app_constants import ColumnNames
from data.calculations import calculate_metrics, _is_liability_series
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_metric_card,
    render_page_hero,
    render_panel_head,
    render_panel_note,
    render_section_intro,
)
from ui.charts import (
    create_donut_chart,
    create_horizontal_bar_chart,
    create_top_accounts_chart,
)


def _format_currency(value: float) -> str:
    """Format currency values consistently for overview cards."""
    return f"${value:,.0f}"


def _format_signed_currency(value: float) -> str:
    """Format currency deltas with a sign."""
    return f"{value:+,.0f}"


def _format_signed_percent(value: float) -> str:
    """Format percentage deltas with a sign."""
    return f"{value:+.2f}%"


def _render_hero(latest_month_label: str, metrics: dict, previous_month_exists: bool) -> None:
    """Render a hero banner for the overview tab."""
    if previous_month_exists:
        direction = (
            "up"
            if metrics["net_worth_change"] > 0
            else "down"
            if metrics["net_worth_change"] < 0
            else "flat"
        )
        direction_text = (
            f"Net worth is {direction} {_format_signed_currency(metrics['net_worth_change'])} "
            f"({_format_signed_percent(metrics['net_worth_pct_change'])}) versus the previous snapshot."
        )
    else:
        direction_text = "Only one snapshot is available, so period-over-period movement is not shown yet."

    render_page_hero(
        "Net Worth",
        "Overview",
        "A quick read on your latest balance, debt load, and where the biggest balances sit.",
        f"Latest snapshot {latest_month_label} | {direction_text}",
    )


def _style_overview_chart(fig, accent_color: str) -> None:
    """Apply a softer chart treatment for the overview page."""
    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(248,250,252,0.55)",
        margin={"l": 24, "r": 12, "t": 52, "b": 24},
        title_font={"size": 18, "color": "#0f172a"},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.18)", zeroline=False)
    fig.update_traces(marker_line_color=accent_color)


def _render_chart_panel(
    tone: str,
    kicker: str,
    title: str,
    copy: str,
    stat_text: str,
    fig,
    title_x: float = 0.08,
) -> None:
    """Render a full chart panel with shared styling."""
    style = NetWorthOverviewConfig.PANEL_STYLES[tone]
    render_panel_head(tone, kicker, title, copy, stat_text)
    _style_overview_chart(fig, style["accent"])
    fig.update_layout(title=title, title_x=title_x)
    st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)


def _build_panel_spec(
    tone: str,
    kicker: str,
    title: str,
    copy: str,
    stat_text: str,
    fig,
    title_x: float = 0.08,
) -> dict:
    """Build a reusable panel specification for rendering."""
    return {
        "tone": tone,
        "kicker": kicker,
        "title": title,
        "copy": copy,
        "stat_text": stat_text,
        "fig": fig,
        "title_x": title_x,
    }


def _render_panel_spec(panel_spec: dict) -> None:
    """Render a chart panel from a reusable spec."""
    _render_chart_panel(
        tone=panel_spec["tone"],
        kicker=panel_spec["kicker"],
        title=panel_spec["title"],
        copy=panel_spec["copy"],
        stat_text=panel_spec["stat_text"],
        fig=panel_spec["fig"],
        title_x=panel_spec.get("title_x", 0.08),
    )


def _render_liability_empty_state() -> None:
    """Render a consistent empty state for the liabilities panel."""
    render_panel_head(
        "liabilities",
        "Liabilities",
        "Debt Snapshot",
        "You currently have no debt balances in the latest view, which keeps this side of the dashboard light.",
        "No liabilities recorded in the current snapshot",
    )
    render_panel_note(
        "No liabilities recorded.",
        "This latest snapshot is currently all positive-side balances.",
    )


def render_dashboard(filtered_df: pd.DataFrame) -> None:
    """Render the overview dashboard for net worth analysis."""
    inject_surface_styles()

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

    liability_mask = _is_liability_series(latest_month_rows)
    holdings_data = latest_month_rows.loc[~liability_mask].copy()
    holdings_by_category = (
        holdings_data.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .sort_values(ascending=False)
    )

    liability_data = latest_month_rows.loc[liability_mask].copy()
    liability_by_category = (
        liability_data.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .abs()
        .sort_values(ascending=False)
        if not liability_data.empty
        else pd.Series(dtype=float)
    )

    top_accounts = latest_month_rows.copy()
    top_accounts[ColumnNames.AMOUNT] = top_accounts[ColumnNames.AMOUNT].abs()
    account_label_column = (
        ColumnNames.ACCOUNT_DISPLAY
        if ColumnNames.ACCOUNT_DISPLAY in top_accounts.columns
        else ColumnNames.ACCOUNT
    )
    top_accounts = top_accounts.nlargest(
        5,
        ColumnNames.AMOUNT,
    )[[account_label_column, ColumnNames.AMOUNT, ColumnNames.CATEGORY]].rename(
        columns={account_label_column: ColumnNames.ACCOUNT}
    )

    account_type_dist = latest_month_rows.copy()
    account_type_dist["display_amount"] = account_type_dist[ColumnNames.AMOUNT].abs()
    account_type_dist = account_type_dist.groupby(ColumnNames.ACCOUNT_TYPE)["display_amount"].sum()

    largest_holding_subtype = holdings_by_category.index[0] if not holdings_by_category.empty else "N/A"
    largest_holding_value = holdings_by_category.iloc[0] if not holdings_by_category.empty else 0
    largest_liability_subtype = liability_by_category.index[0] if not liability_by_category.empty else "None"
    largest_liability_value = liability_by_category.iloc[0] if not liability_by_category.empty else 0
    dominant_account_type = account_type_dist.idxmax() if not account_type_dist.empty else "N/A"
    dominant_account_share = (
        account_type_dist.max() / account_type_dist.sum() * 100
        if not account_type_dist.empty and account_type_dist.sum() > 0
        else 0
    )
    leading_account = top_accounts.iloc[0][ColumnNames.ACCOUNT] if not top_accounts.empty else "N/A"
    leading_account_value = top_accounts.iloc[0][ColumnNames.AMOUNT] if not top_accounts.empty else 0

    _render_hero(latest_month_label, metrics, previous_month_exists)

    card_columns = st.columns(3)
    with card_columns[0]:
        render_metric_card(
            "Net Worth",
            _format_currency(metrics["current_net_worth"]),
            (
                f"{_format_signed_currency(metrics['net_worth_change'])} | {_format_signed_percent(metrics['net_worth_pct_change'])}"
                if previous_month_exists
                else "No prior comparison yet"
            ),
            "Your current net worth after liabilities are netted out.",
            "positive" if metrics["net_worth_change"] > 0 else "negative" if metrics["net_worth_change"] < 0 else "neutral",
        )
    with card_columns[1]:
        render_metric_card(
            "Total Liabilities",
            _format_currency(metrics["current_liabilities"]),
            (
                _format_signed_percent(metrics["liabilities_change_pct"])
                if previous_month_exists
                else "No prior comparison yet"
            ),
            "Debt balances in the latest snapshot.",
            "negative" if metrics["current_liabilities"] > 0 else "neutral",
        )
    with card_columns[2]:
        render_metric_card(
            "Debt Ratio",
            f"{metrics['debt_ratio']:.1f}%",
            (
                "Low leverage"
                if metrics["debt_ratio"] < 20
                else "Moderate leverage"
                if metrics["debt_ratio"] < 40
                else "Higher leverage"
            ),
            "Liabilities as a share of the total balance structure.",
            "neutral",
        )

    st.markdown("")
    render_section_intro(
        "Balance Structure",
        "See what is supporting net worth and where debt is pulling against it.",
    )
    render_accent_pills(
        [
            ("Largest Subtype", f"{largest_holding_subtype} | {_format_currency(largest_holding_value)}"),
            ("Debt Pressure", f"{metrics['debt_ratio']:.1f}% of balance structure"),
            ("Latest Snapshot", latest_month_label),
        ]
    )
    holdings_col, liabilities_col = st.columns(2)

    holdings_panel = _build_panel_spec(
        "assets",
        "Strengths",
        "Holdings by Account Subtype",
        "See which subtypes carry the most weight in the latest snapshot.",
        f"Top subtype: {largest_holding_subtype} at {_format_currency(largest_holding_value)}",
        create_horizontal_bar_chart(
            holdings_by_category,
            "Holdings by Account Subtype",
            "networth",
            metrics["current_assets"],
        ),
    )

    liability_panel = _build_panel_spec(
        "liabilities",
        "Liabilities",
        "Liabilities by Account Subtype",
        "See where debt is concentrated in the latest snapshot.",
        f"Largest liability subtype: {largest_liability_subtype} at {_format_currency(largest_liability_value)}",
        create_horizontal_bar_chart(
            liability_by_category,
            "Liabilities by Account Subtype",
            "networth",
            metrics["current_liabilities"],
        ),
    ) if not liability_data.empty else None

    with holdings_col:
        _render_panel_spec(holdings_panel)

    with liabilities_col:
        if liability_panel is None:
            _render_liability_empty_state()
        else:
            _render_panel_spec(liability_panel)

    st.markdown("")
    render_section_intro(
        "Composition",
        "Review the latest mix and the balances with the most weight.",
    )
    render_accent_pills(
        [
            ("Dominant Type", f"{dominant_account_type} | {dominant_account_share:.1f}%"),
            ("Largest Account", f"{leading_account} | {_format_currency(leading_account_value)}"),
        ]
    )
    composition_col, top_accounts_col = st.columns([1, 1.15])

    composition_panel = _build_panel_spec(
        "neutral",
        "Mix",
        "Account Type Mix",
        "Review the latest balance mix across major account types.",
        f"Dominant type: {dominant_account_type} at {dominant_account_share:.1f}%",
        create_donut_chart(account_type_dist, "Account Type Mix", color_scheme='networth'),
        title_x=0.12,
    )

    top_accounts_panel = _build_panel_spec(
        "neutral",
        "Leaders",
        "Largest Accounts",
        "The balances with the most weight in the latest snapshot.",
        f"Leading account: {leading_account} at {_format_currency(leading_account_value)}",
        create_top_accounts_chart(top_accounts, color_scheme='networth'),
    )

    with composition_col:
        _render_panel_spec(composition_panel)

    with top_accounts_col:
        _render_panel_spec(top_accounts_panel)

