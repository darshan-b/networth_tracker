"""Overview dashboard for the Net Worth Tracker."""

import pandas as pd
import streamlit as st

from config import ChartConfig
from app_constants import AccountTypes, ColumnNames
from data.calculations import calculate_metrics
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


def _inject_dashboard_styles() -> None:
    """Apply a more intentional visual treatment to the overview tab."""
    st.markdown(
        """
        <style>
        .nw-hero {
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.18), transparent 34%),
                linear-gradient(135deg, #f7faf9 0%, #eef7f3 52%, #f8f5ef 100%);
            border: 1px solid rgba(15, 118, 110, 0.16);
            border-radius: 24px;
            padding: 1.5rem 1.7rem;
            margin-bottom: 1rem;
        }
        .nw-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.78rem;
            font-weight: 600;
            color: #0f766e;
            margin-bottom: 0.45rem;
        }
        .nw-title {
            font-size: 2rem;
            line-height: 1.1;
            font-weight: 700;
            color: #111827;
            margin: 0;
        }
        .nw-subtitle {
            margin-top: 0.6rem;
            color: #4b5563;
            font-size: 0.98rem;
            max-width: 54rem;
        }
        .nw-hero-meta {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 1rem;
            padding: 0.45rem 0.7rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.8);
            color: #1f2937;
            font-size: 0.88rem;
        }
        .nw-card {
            background: linear-gradient(180deg, #ffffff 0%, #fbfcfd 100%);
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 22px;
            padding: 1rem 1.05rem;
            min-height: 148px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
        }
        .nw-card-label {
            color: #6b7280;
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }
        .nw-card-value {
            color: #111827;
            font-size: 1.75rem;
            line-height: 1.1;
            font-weight: 700;
            margin-top: 0.55rem;
        }
        .nw-card-delta {
            margin-top: 0.55rem;
            font-size: 0.95rem;
            font-weight: 600;
        }
        .nw-card-delta.positive { color: #0f766e; }
        .nw-card-delta.negative { color: #b91c1c; }
        .nw-card-delta.neutral { color: #475569; }
        .nw-card-caption {
            color: #6b7280;
            font-size: 0.88rem;
            margin-top: 0.7rem;
        }
        .nw-section-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.25rem;
        }
        .nw-section-copy {
            color: #6b7280;
            font-size: 0.95rem;
            margin-bottom: 0.9rem;
        }
        .nw-accent-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-bottom: 1rem;
        }
        .nw-accent-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.75rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(15, 23, 42, 0.08);
            color: #334155;
            font-size: 0.86rem;
        }
        .nw-panel-head {
            border-radius: 20px;
            padding: 0.95rem 1rem;
            margin-bottom: 0.6rem;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: linear-gradient(180deg, #ffffff 0%, #f8fbfa 100%);
        }
        .nw-panel-head.assets {
            background: linear-gradient(180deg, #f5fbf7 0%, #edf8f2 100%);
            border-color: rgba(15, 118, 110, 0.12);
        }
        .nw-panel-head.liabilities {
            background: linear-gradient(180deg, #fff7f7 0%, #fff0f0 100%);
            border-color: rgba(185, 28, 28, 0.12);
        }
        .nw-panel-head.composition {
            background: linear-gradient(180deg, #f8f8fc 0%, #f4f2fb 100%);
            border-color: rgba(67, 56, 202, 0.12);
        }
        .nw-panel-kicker {
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.76rem;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 0.3rem;
        }
        .nw-panel-title {
            color: #0f172a;
            font-size: 1.02rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .nw-panel-copy {
            color: #64748b;
            font-size: 0.9rem;
        }
        .nw-panel-stat {
            margin-top: 0.75rem;
            font-size: 0.88rem;
            color: #1f2937;
            font-weight: 600;
        }
        .nw-panel-note {
            padding: 0.9rem 1rem;
            border-radius: 18px;
            background: linear-gradient(180deg, #f9fafb 0%, #f3f6f8 100%);
            border: 1px dashed rgba(100, 116, 139, 0.35);
            color: #475569;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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

    st.markdown(
        f"""
        <div class="nw-hero">
            <div class="nw-eyebrow">Net Worth Tracker</div>
            <p class="nw-title">A cleaner view of where you stand right now.</p>
            <div class="nw-subtitle">
                This overview is designed to answer the big questions first: your current net worth,
                balance mix, debt pressure, and the accounts shaping the latest snapshot.
            </div>
            <div class="nw-hero-meta">
                <span>Latest snapshot</span>
                <strong>{latest_month_label}</strong>
                <span>&middot;</span>
                <span>{direction_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_metric_card(
    label: str,
    value: str,
    delta: str,
    caption: str,
    tone: str = "neutral",
) -> None:
    """Render a styled KPI card."""
    st.markdown(
        f"""
        <div class="nw-card">
            <div class="nw-card-label">{label}</div>
            <div class="nw-card-value">{value}</div>
            <div class="nw-card-delta {tone}">{delta}</div>
            <div class="nw-card-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_section_header(title: str, copy: str) -> None:
    """Render a compact section header."""
    st.markdown(
        f"""
        <div class="nw-section-title">{title}</div>
        <div class="nw-section-copy">{copy}</div>
        """,
        unsafe_allow_html=True,
    )


def _render_accent_pills(items: list[tuple[str, str]]) -> None:
    """Render compact visual summary pills."""
    pills_html = "".join(
        [
            f"<div class='nw-accent-pill'><strong>{label}</strong><span>{value}</span></div>"
            for label, value in items
        ]
    )
    st.markdown(f"<div class='nw-accent-row'>{pills_html}</div>", unsafe_allow_html=True)


def _render_panel_head(
    tone: str,
    kicker: str,
    title: str,
    copy: str,
    stat_text: str,
) -> None:
    """Render a styled intro block for a lower-half chart panel."""
    st.markdown(
        f"""
        <div class="nw-panel-head {tone}">
            <div class="nw-panel-kicker">{kicker}</div>
            <div class="nw-panel-title">{title}</div>
            <div class="nw-panel-copy">{copy}</div>
            <div class="nw-panel-stat">{stat_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
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


def render_dashboard(filtered_df: pd.DataFrame) -> None:
    """Render the overview dashboard for net worth analysis."""
    _inject_dashboard_styles()

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

    holdings_data = latest_month_rows[
        latest_month_rows[ColumnNames.ACCOUNT_TYPE] != AccountTypes.LIABILITY
    ]
    holdings_by_category = (
        holdings_data.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .sort_values(ascending=False)
    )

    liability_data = latest_month_rows[
        latest_month_rows[ColumnNames.ACCOUNT_TYPE] == AccountTypes.LIABILITY
    ]
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

    card_columns = st.columns(4)
    with card_columns[0]:
        _render_metric_card(
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
        _render_metric_card(
            "Total Assets",
            _format_currency(metrics["current_assets"]),
            f"{len(holdings_data[ColumnNames.ACCOUNT_KEY].unique()) if ColumnNames.ACCOUNT_KEY in holdings_data.columns else len(holdings_data[ColumnNames.ACCOUNT].unique())} active accounts",
            "Positive balances across your latest asset holdings.",
            "neutral",
        )
    with card_columns[2]:
        _render_metric_card(
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
    with card_columns[3]:
        _render_metric_card(
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
    _render_section_header(
        "Where Your Balance Sits",
        "A side-by-side read of what is supporting your net worth and where debt is pulling against it.",
    )
    _render_accent_pills(
        [
            ("Largest Subtype", f"{largest_holding_subtype} | {_format_currency(largest_holding_value)}"),
            ("Debt Pressure", f"{metrics['debt_ratio']:.1f}% of balance structure"),
            ("Latest Snapshot", latest_month_label),
        ]
    )
    holdings_col, liabilities_col = st.columns(2)

    with holdings_col:
        _render_panel_head(
            "assets",
            "Strengths",
            "Holdings by Account Subtype",
            "See which account subtypes are doing the most work for your current net worth.",
            f"Top subtype: {largest_holding_subtype} at {_format_currency(largest_holding_value)}",
        )
        fig_holdings = create_horizontal_bar_chart(
            holdings_by_category,
            "Holdings by Account Subtype",
            "assets",
            metrics["current_assets"],
        )
        _style_overview_chart(fig_holdings, "rgba(15, 118, 110, 0.22)")
        fig_holdings.update_layout(title_x=0.08)
        st.plotly_chart(fig_holdings, config=ChartConfig.STREAMLIT_CONFIG)

    with liabilities_col:
        if liability_data.empty:
            _render_panel_head(
                "liabilities",
                "Liabilities",
                "Debt Snapshot",
                "You currently have no debt balances in the latest view, which keeps this side of the dashboard light.",
                "No liabilities recorded in the current snapshot",
            )
            st.markdown(
                """
                <div class="nw-panel-note">
                    <strong>No liabilities recorded.</strong><br>
                    This latest snapshot is currently all positive-side balances.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            _render_panel_head(
                "liabilities",
                "Liabilities",
                "Liabilities by Account Subtype",
                "This panel shows where debt is concentrated so risk feels easier to read at a glance.",
                f"Largest liability subtype: {largest_liability_subtype} at {_format_currency(largest_liability_value)}",
            )
            fig_liabilities = create_horizontal_bar_chart(
                liability_by_category,
                "Liabilities by Account Subtype",
                "liabilities",
                metrics["current_liabilities"],
            )
            _style_overview_chart(fig_liabilities, "rgba(185, 28, 28, 0.22)")
            fig_liabilities.update_layout(title_x=0.08)
            st.plotly_chart(fig_liabilities, config=ChartConfig.STREAMLIT_CONFIG)

    st.markdown("")
    _render_section_header(
        "Composition At A Glance",
        "This layer shows how the latest snapshot breaks down across account types and which balances matter most.",
    )
    _render_accent_pills(
        [
            ("Dominant Type", f"{dominant_account_type} | {dominant_account_share:.1f}%"),
            ("Largest Account", f"{leading_account} | {_format_currency(leading_account_value)}"),
        ]
    )
    composition_col, top_accounts_col = st.columns([1, 1.15])

    with composition_col:
        _render_panel_head(
            "composition",
            "Mix",
            "Account Type Mix",
            "A quick composition view to show whether your latest balance is concentrated in a few major buckets.",
            f"Dominant type: {dominant_account_type} at {dominant_account_share:.1f}%",
        )
        fig_type = create_donut_chart(account_type_dist, "Account Type Mix")
        _style_overview_chart(fig_type, "rgba(67, 56, 202, 0.18)")
        fig_type.update_layout(title_x=0.12)
        st.plotly_chart(fig_type, config=ChartConfig.STREAMLIT_CONFIG)

    with top_accounts_col:
        _render_panel_head(
            "composition",
            "Leaders",
            "Largest Accounts",
            "The accounts with the most weight in the current snapshot, useful for concentration awareness.",
            f"Leading account: {leading_account} at {_format_currency(leading_account_value)}",
        )
        fig_top = create_top_accounts_chart(top_accounts)
        _style_overview_chart(fig_top, "rgba(67, 56, 202, 0.18)")
        fig_top.update_layout(title="Largest Accounts", title_x=0.08)
        st.plotly_chart(fig_top, config=ChartConfig.STREAMLIT_CONFIG)
