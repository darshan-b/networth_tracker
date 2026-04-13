"""Product-style trend analysis view for Net Worth Tracker."""

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app_constants import ColumnNames
from config import ChartConfig, ColorSchemes
from data.calculations import _is_liability_series
from ui.components.networth_d3 import (
    render_networth_drivers_d3,
    render_networth_overview_d3,
)
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_metric_card,
    render_page_hero,
    render_panel_head,
    render_section_intro,
)


BREAKDOWN_LABELS = {
    ColumnNames.CATEGORY: "Account Subtype",
    ColumnNames.ACCOUNT_TYPE: "Account Type",
    ColumnNames.INSTITUTION: "Financial Institution",
    "type_subtype": "Account Type + Account Subtype",
}

VIEW_MODES = ["Overview", "Drivers", "Composition"]
VIEW_PRESETS = ["Standard", "With Trend Line", "With 3-month Average"]
PERIOD_OPTIONS = ["Monthly", "Quarterly", "Yearly"]
MILESTONES = [100000, 250000, 500000, 750000, 1000000, 1500000, 2000000]


def _format_currency(amount: float) -> str:
    return f"${amount:,.0f}"


def _round_to_k(amount: float) -> str:
    if abs(amount) >= 1_000_000:
        return f"{amount/1_000_000:.1f}M".replace(".0M", "M")
    if abs(amount) >= 1_000:
        return f"{amount/1_000:.0f}K"
    return f"{amount:,.0f}"


def _prepare_period_data(filtered_df: pd.DataFrame, period_comparison: str) -> tuple[pd.DataFrame, str, str]:
    df = filtered_df.copy()
    df["Date"] = pd.to_datetime(df[ColumnNames.MONTH])
    df["Quarter"] = df["Date"].dt.to_period("Q").astype(str)
    df["Year"] = df["Date"].dt.year.astype(str)

    interval_map = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}
    interval = interval_map[period_comparison]

    all_months = df.sort_values("Date")[ColumnNames.MONTH].unique()
    selected_indices = list(range(len(all_months) - 1, -1, -interval))[::-1]
    if selected_indices and selected_indices[0] > 0:
        selected_indices.insert(0, 0)
    selected_months = [all_months[i] for i in selected_indices]

    df = df[df[ColumnNames.MONTH].isin(selected_months)].copy()

    if period_comparison == "Quarterly":
        df["Period"] = df["Quarter"]
        df["Period_Str"] = df["Quarter"]
    elif period_comparison == "Yearly":
        df["Period"] = df["Year"]
        df["Period_Str"] = df["Year"]
    else:
        df["Period"] = df[ColumnNames.MONTH]
        df["Period_Str"] = df[ColumnNames.MONTH_STR]

    return df, "Period", "Period_Str"


def _aggregate_trend_data(
    period_filtered_df: pd.DataFrame,
    breakdown_key: str,
    period_col: str,
    period_str_col: str,
) -> tuple[pd.DataFrame, str, str]:
    if breakdown_key == ColumnNames.CATEGORY:
        agg_df = period_filtered_df.groupby(
            [period_col, period_str_col, ColumnNames.CATEGORY],
            as_index=False,
        )[ColumnNames.AMOUNT].sum()
        return agg_df, ColumnNames.CATEGORY, BREAKDOWN_LABELS[ColumnNames.CATEGORY]

    if breakdown_key == ColumnNames.ACCOUNT_TYPE:
        agg_df = period_filtered_df.groupby(
            [period_col, period_str_col, ColumnNames.ACCOUNT_TYPE],
            as_index=False,
        )[ColumnNames.AMOUNT].sum()
        return agg_df, ColumnNames.ACCOUNT_TYPE, BREAKDOWN_LABELS[ColumnNames.ACCOUNT_TYPE]

    if breakdown_key == ColumnNames.INSTITUTION:
        agg_df = period_filtered_df.groupby(
            [period_col, period_str_col, ColumnNames.INSTITUTION],
            as_index=False,
        )[ColumnNames.AMOUNT].sum()
        return agg_df, ColumnNames.INSTITUTION, BREAKDOWN_LABELS[ColumnNames.INSTITUTION]

    working_df = period_filtered_df.copy()
    working_df["Group"] = (
        working_df[ColumnNames.ACCOUNT_TYPE].astype(str)
        + " / "
        + working_df[ColumnNames.CATEGORY].astype(str)
    )
    agg_df = working_df.groupby([period_col, period_str_col, "Group"], as_index=False)[ColumnNames.AMOUNT].sum()
    return agg_df, "Group", BREAKDOWN_LABELS["type_subtype"]


def _build_totals_df(
    agg_df: pd.DataFrame,
    period_col: str,
    period_str_col: str,
    show_rolling_avg: bool,
) -> pd.DataFrame:
    totals_df = agg_df.groupby([period_col, period_str_col], as_index=False)[ColumnNames.AMOUNT].sum()
    totals_df = totals_df.sort_values(period_col).reset_index(drop=True)
    totals_df["Period_Pct"] = totals_df[ColumnNames.AMOUNT].pct_change() * 100
    totals_df["Period_Pct_Text"] = totals_df["Period_Pct"].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else ""
    )
    if show_rolling_avg and len(totals_df) >= 3:
        totals_df["Rolling_Avg"] = totals_df[ColumnNames.AMOUNT].rolling(window=3, min_periods=1).mean()
    return totals_df


def _create_plotly_trend_chart(
    agg_df: pd.DataFrame,
    totals_df: pd.DataFrame,
    period_col: str,
    period_str_col: str,
    color_column: str,
    legend_title: str,
    period_comparison: str,
    show_trend_line: bool,
    show_rolling_avg: bool,
    show_milestones: bool,
    highlight_extremes: bool,
    show_period_pct: bool,
) -> go.Figure:
    fig = px.bar(
        agg_df,
        x=period_col,
        y=ColumnNames.AMOUNT,
        color=color_column,
        text=None,
        barmode="stack",
        hover_data={period_col: False, ColumnNames.AMOUNT: True, color_column: True},
        color_discrete_sequence=ColorSchemes.NETWORTH,
    )

    if show_trend_line:
        fig.add_trace(
            go.Scatter(
                x=totals_df[period_col],
                y=totals_df[ColumnNames.AMOUNT],
                mode="lines+markers",
                name="Total Net Worth",
                line=dict(width=3, color="#0F766E"),
                marker=dict(size=8, symbol="diamond"),
                hovertemplate="<b>Total:</b> $%{y:,.0f}<extra></extra>",
            )
        )

    if show_rolling_avg and "Rolling_Avg" in totals_df.columns:
        fig.add_trace(
            go.Scatter(
                x=totals_df[period_col],
                y=totals_df["Rolling_Avg"],
                mode="lines",
                name="3-month Average",
                line=dict(color="#D97706", width=2, dash="dash"),
                hovertemplate="<b>3-Mo Avg:</b> $%{y:,.0f}<extra></extra>",
            )
        )

    if show_milestones:
        min_nw = totals_df[ColumnNames.AMOUNT].min()
        max_nw = totals_df[ColumnNames.AMOUNT].max()
        for milestone in MILESTONES:
            if min_nw < milestone < max_nw:
                fig.add_hline(
                    y=milestone,
                    line_dash="dot",
                    line_color="rgba(217, 119, 6, 0.45)",
                    annotation_text=_round_to_k(milestone),
                    annotation_position="top right",
                )

    if highlight_extremes and len(totals_df) >= 2:
        best_idx = totals_df[ColumnNames.AMOUNT].idxmax()
        worst_idx = totals_df[ColumnNames.AMOUNT].idxmin()
        fig.add_annotation(
            x=totals_df.loc[best_idx, period_col],
            y=totals_df.loc[best_idx, ColumnNames.AMOUNT],
            text=f"Best | {_format_currency(totals_df.loc[best_idx, ColumnNames.AMOUNT])}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-50,
            bgcolor="#DCFCE7",
        )
        fig.add_annotation(
            x=totals_df.loc[worst_idx, period_col],
            y=totals_df.loc[worst_idx, ColumnNames.AMOUNT],
            text=f"Lowest | {_format_currency(totals_df.loc[worst_idx, ColumnNames.AMOUNT])}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=50,
            bgcolor="#FEE2E2",
        )

    fig.add_trace(
        go.Scatter(
            x=totals_df[period_col],
            y=totals_df[ColumnNames.AMOUNT],
            text=totals_df[ColumnNames.AMOUNT].apply(_round_to_k),
            textposition="top center",
            mode="text",
            showlegend=False,
            textfont=dict(size=13, family=ChartConfig.FONT["family"]),
            name="Totals",
        )
    )

    if show_period_pct:
        fig.add_trace(
            go.Scatter(
                x=totals_df[period_col],
                y=totals_df[ColumnNames.AMOUNT] * 1.10,
                text=totals_df["Period_Pct_Text"],
                textposition="middle center",
                mode="text",
                showlegend=False,
                textfont=dict(size=12, family=ChartConfig.FONT["family"]),
                name="Period change",
            )
        )

    period_label = period_comparison[:-2] if period_comparison != "Monthly" else "Month"
    fig.update_layout(
        title={"text": f"{period_comparison} Net Worth Trend", "x": 0.45, "xanchor": "center"},
        title_font={"size": 20},
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(248,250,252,0.55)",
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor="rgba(15, 23, 42, 0.10)",
            font=dict(
                family=ChartConfig.FONT["family"],
                size=13,
                color="#0f172a",
            ),
        ),
        xaxis=dict(
            tickvals=totals_df[period_col],
            ticktext=totals_df[period_str_col],
            title=period_label,
            tickangle=90 if period_comparison == "Monthly" else 45,
        ),
        yaxis=dict(title="Amount ($)", tickprefix="$", tickformat=",.0f"),
        legend_title=legend_title,
        hovermode="x unified",
        height=700,
        font=ChartConfig.FONT,
        margin={"l": 36, "r": 24, "t": 64, "b": 54},
    )
    fig.update_traces(
        selector=dict(type="bar"),
        marker_line_width=0,
        marker_line_color="rgba(0,0,0,0)",
        marker=dict(cornerradius=10),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.14)", zeroline=False, nticks=5)
    return fig


def _build_overview_payload(
    period_filtered_df: pd.DataFrame,
    agg_df: pd.DataFrame,
    totals_df: pd.DataFrame,
    period_col: str,
    period_str_col: str,
    color_column: str,
    legend_title: str,
    show_trend_line: bool,
    show_rolling_avg: bool,
    show_milestones: bool,
    highlight_extremes: bool,
    show_period_pct: bool,
) -> dict:
    asset_liability_rows = []
    for period_value, period_label in totals_df[[period_col, period_str_col]].itertuples(index=False):
        period_slice = period_filtered_df[period_filtered_df[period_col] == period_value].copy()
        liability_mask = _is_liability_series(period_slice)
        liabilities = abs(period_slice.loc[liability_mask, ColumnNames.AMOUNT].sum())
        assets = period_slice.loc[~liability_mask, ColumnNames.AMOUNT].sum()
        total = period_slice[ColumnNames.AMOUNT].sum()
        asset_liability_rows.append(
            {
                "period": str(period_value),
                "label": str(period_label),
                "total": float(total),
                "assets": float(assets),
                "liabilities": float(liabilities),
            }
        )

    pivot_df = (
        agg_df.assign(_series_name=agg_df[color_column].astype(str))
        .pivot_table(
            index=[period_col, period_str_col],
            columns="_series_name",
            values=ColumnNames.AMOUNT,
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    value_columns = [col for col in pivot_df.columns if col not in [period_col, period_str_col]]
    category_priority = (
        pivot_df[value_columns]
        .abs()
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )
    top_categories = category_priority[:6]
    other_categories = [category for category in value_columns if category not in top_categories]

    if other_categories:
        pivot_df["Other"] = pivot_df[other_categories].sum(axis=1)
        categories = top_categories + ["Other"]
    else:
        categories = top_categories

    rows = []
    for _, row in totals_df.iterrows():
        matching = pivot_df[pivot_df[period_col] == row[period_col]]
        base_row = next(item for item in asset_liability_rows if item["period"] == str(row[period_col]))
        categories_map = {
            category: float(matching.iloc[0][category]) if not matching.empty and category in matching.columns else 0.0
            for category in categories
        }
        rows.append(
            {
                **base_row,
                "pctText": row.get("Period_Pct_Text", "") if pd.notna(row.get("Period_Pct_Text", "")) else "",
                "pctValue": float(row["Period_Pct"]) if pd.notna(row.get("Period_Pct")) else 0.0,
                "rollingAvg": float(row["Rolling_Avg"]) if "Rolling_Avg" in totals_df.columns and pd.notna(row.get("Rolling_Avg")) else None,
                "categories": categories_map,
            }
        )

    milestones = []
    if show_milestones:
        min_nw = float(totals_df[ColumnNames.AMOUNT].min())
        max_nw = float(totals_df[ColumnNames.AMOUNT].max())
        milestones = [milestone for milestone in MILESTONES if min_nw < milestone < max_nw]

    return {
        "rows": rows,
        "categories": categories,
        "colors": ColorSchemes.NETWORTH,
        "showTrendLine": show_trend_line,
        "showRollingAvg": show_rolling_avg,
        "showMilestones": show_milestones,
        "highlightExtremes": highlight_extremes,
        "showPeriodPct": show_period_pct,
        "milestones": milestones,
        "legendTitle": legend_title,
    }


def _build_drivers_df(
    agg_df: pd.DataFrame,
    color_column: str,
    from_period: str,
    to_period: str,
) -> pd.DataFrame:
    from_df = agg_df[agg_df["Period_Str"] == from_period][[color_column, ColumnNames.AMOUNT]].rename(
        columns={ColumnNames.AMOUNT: "previous"}
    )
    to_df = agg_df[agg_df["Period_Str"] == to_period][[color_column, ColumnNames.AMOUNT]].rename(
        columns={ColumnNames.AMOUNT: "current"}
    )

    drivers_df = from_df.merge(to_df, on=color_column, how="outer").fillna(0)
    drivers_df["delta"] = drivers_df["current"] - drivers_df["previous"]
    drivers_df = drivers_df.sort_values("delta", ascending=False)
    return drivers_df


def _select_comparison_periods(period_labels: list[str]) -> tuple[str, str]:
    """Render shared period selectors for change-based views."""
    selector_col1, selector_col2 = st.columns(2)
    with selector_col1:
        from_period = st.selectbox(
            "Compare From",
            period_labels[:-1],
            index=max(len(period_labels[:-1]) - 1, 0),
            key="networth_compare_from",
        )
    with selector_col2:
        valid_to_periods = period_labels[period_labels.index(from_period) + 1 :]
        to_period = st.selectbox(
            "Compare To",
            valid_to_periods,
            index=len(valid_to_periods) - 1,
            key="networth_compare_to",
        )
    return from_period, to_period


def _render_summary_cards(totals_df: pd.DataFrame) -> None:
    current_nw = totals_df.iloc[-1][ColumnNames.AMOUNT]
    previous_nw = totals_df.iloc[-2][ColumnNames.AMOUNT]
    first_nw = totals_df.iloc[0][ColumnNames.AMOUNT]

    period_change = current_nw - previous_nw
    period_pct = (period_change / abs(previous_nw)) * 100 if previous_nw != 0 else 0
    total_change = current_nw - first_nw
    total_pct = (total_change / abs(first_nw)) * 100 if first_nw != 0 else 0
    avg_growth = total_change / len(totals_df) if len(totals_df) else 0

    if len(totals_df) >= 3:
        previous_change = totals_df.iloc[-2][ColumnNames.AMOUNT] - totals_df.iloc[-3][ColumnNames.AMOUNT]
        velocity = period_change - previous_change
        velocity_text = "Accelerating" if velocity > 0 else "Decelerating" if velocity < 0 else "Steady"
    else:
        velocity_text = "Short history"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "Current Net Worth",
            _format_currency(current_nw),
            f"{period_change:,.0f} ({period_pct:+.2f}%)",
            "Latest period-over-period movement.",
            "positive" if period_change > 0 else "negative" if period_change < 0 else "neutral",
        )
    with col2:
        render_metric_card(
            "Total Growth",
            _format_currency(total_change),
            f"{total_pct:+.2f}%",
            "Change from the first tracked period to now.",
            "positive" if total_change > 0 else "negative" if total_change < 0 else "neutral",
        )
    with col3:
        render_metric_card(
            "Periods Tracked",
            str(len(totals_df)),
            "History depth",
            "Number of snapshots included in this trend view.",
            "neutral",
        )
    with col4:
        render_metric_card(
            "Average Period Growth",
            _format_currency(avg_growth),
            velocity_text,
            "Average pace of change across the tracked history.",
            "positive" if avg_growth > 0 else "negative" if avg_growth < 0 else "neutral",
        )


def _render_overview_mode(
    period_filtered_df: pd.DataFrame,
    agg_df: pd.DataFrame,
    totals_df: pd.DataFrame,
    period_col: str,
    period_str_col: str,
    color_column: str,
    legend_title: str,
    period_comparison: str,
    show_trend_line: bool,
    show_rolling_avg: bool,
    show_milestones: bool,
    highlight_extremes: bool,
    show_period_pct: bool,
) -> None:
    latest_total = totals_df.iloc[-1][ColumnNames.AMOUNT]
    previous_total = totals_df.iloc[-2][ColumnNames.AMOUNT]
    net_change = latest_total - previous_total

    latest_breakdown = (
        agg_df[agg_df[period_str_col] == totals_df.iloc[-1][period_str_col]]
        .sort_values(ColumnNames.AMOUNT, ascending=False)
        .reset_index(drop=True)
    )
    leading_bucket = latest_breakdown.iloc[0][color_column] if not latest_breakdown.empty else "N/A"
    leading_value = latest_breakdown.iloc[0][ColumnNames.AMOUNT] if not latest_breakdown.empty else 0
    strongest_positive = latest_breakdown[latest_breakdown[ColumnNames.AMOUNT] > 0]
    if len(totals_df) >= 2:
        previous_label = totals_df.iloc[-2][period_str_col]
        current_label = totals_df.iloc[-1][period_str_col]
        drivers_df = _build_drivers_df(agg_df, color_column, previous_label, current_label)
        positive_drivers = drivers_df[drivers_df["delta"] > 0]
        negative_drivers = drivers_df[drivers_df["delta"] < 0]
        leading_lift = (
            f"{positive_drivers.iloc[0][color_column]} | {_format_currency(positive_drivers.iloc[0]['delta'])}"
            if not positive_drivers.empty
            else "No positive lift"
        )
        leading_drag = (
            f"{negative_drivers.iloc[0][color_column]} | {_format_currency(abs(negative_drivers.iloc[0]['delta']))}"
            if not negative_drivers.empty
            else "No drag"
        )
    else:
        leading_lift = "Not available"
        leading_drag = "Not available"

    render_panel_head(
        "neutral",
        "Overview",
        "Net Worth Story At A Glance",
        "Start with the full trend, then switch views only when you need more detail.",
        f"Current net change: {_format_currency(net_change)} versus the previous {period_comparison.lower()} period",
    )
    render_accent_pills(
        [
            ("Leading Bucket", f"{leading_bucket} | {_format_currency(leading_value)}"),
            ("Strongest Lift", leading_lift),
            ("Largest Drag", leading_drag),
            ("Current Period", str(totals_df.iloc[-1][period_str_col])),
        ]
    )

    render_networth_overview_d3(
        _build_overview_payload(
            period_filtered_df=period_filtered_df,
            agg_df=agg_df,
            totals_df=totals_df,
            period_col=period_col,
            period_str_col=period_str_col,
            color_column=color_column,
            legend_title=legend_title,
            show_trend_line=show_trend_line,
            show_rolling_avg=show_rolling_avg,
            show_milestones=show_milestones,
            highlight_extremes=highlight_extremes,
            show_period_pct=show_period_pct,
        )
    )


def _render_drivers_mode(
    agg_df: pd.DataFrame,
    color_column: str,
    legend_title: str,
) -> None:
    period_labels = agg_df["Period_Str"].drop_duplicates().tolist()
    if len(period_labels) < 2:
        st.warning("Need at least two periods to analyze change drivers.")
        return

    from_period, to_period = _select_comparison_periods(period_labels)

    drivers_df = _build_drivers_df(agg_df, color_column, from_period, to_period)
    drivers_df = drivers_df[drivers_df["delta"] != 0].copy()
    if drivers_df.empty:
        st.info("No meaningful changes found between the selected periods.")
        return

    drivers_df["label"] = drivers_df[color_column].astype(str)
    drivers_df = drivers_df.reindex(drivers_df["delta"].abs().sort_values(ascending=False).index).head(10)

    biggest_gain = drivers_df.loc[drivers_df["delta"].idxmax()]
    biggest_drag = drivers_df.loc[drivers_df["delta"].idxmin()]
    net_delta = drivers_df["delta"].sum()

    render_panel_head(
        "neutral",
        "Drivers",
        "What Changed",
        "Rank the biggest movers between any two periods.",
        f"Net change from {from_period} to {to_period}: {_format_currency(net_delta)}",
    )
    render_accent_pills(
        [
            ("Biggest Lift", f"{biggest_gain['label']} | {_format_currency(biggest_gain['delta'])}"),
            ("Biggest Drag", f"{biggest_drag['label']} | {_format_currency(biggest_drag['delta'])}"),
            ("Breakdown", legend_title),
        ]
    )

    render_networth_drivers_d3(
        {
            "rows": drivers_df[["label", "previous", "current", "delta"]].to_dict("records"),
            "fromLabel": from_period,
            "toLabel": to_period,
        }
    )

    with st.expander("Driver Table", expanded=False):
        display_df = drivers_df[[color_column, "previous", "current", "delta"]].rename(
            columns={
                color_column: legend_title,
                "previous": from_period,
                "current": to_period,
                "delta": "Change",
            }
        )
        st.dataframe(display_df, width="stretch", hide_index=True)


def _render_composition_mode(
    agg_df: pd.DataFrame,
    totals_df: pd.DataFrame,
    period_col: str,
    period_str_col: str,
    color_column: str,
    legend_title: str,
    period_comparison: str,
    show_trend_line: bool,
    show_rolling_avg: bool,
    show_milestones: bool,
    highlight_extremes: bool,
    show_period_pct: bool,
) -> None:
    render_panel_head(
        "neutral",
        "Composition",
        "How Net Worth Is Built Over Time",
        "Use this when you want the full interactive breakdown instead of the cleaner overview.",
        f"Breakdown shown by {legend_title.lower()} in the full analysis chart",
    )
    render_accent_pills(
        [
            ("Primary Lens", legend_title),
            ("View Type", "Advanced Plotly analysis"),
            ("Current Period", str(totals_df.iloc[-1][period_str_col])),
        ]
    )

    fig = _create_plotly_trend_chart(
        agg_df=agg_df,
        totals_df=totals_df,
        period_col=period_col,
        period_str_col=period_str_col,
        color_column=color_column,
        legend_title=legend_title,
        period_comparison=period_comparison,
        show_trend_line=show_trend_line,
        show_rolling_avg=show_rolling_avg,
        show_milestones=show_milestones,
        highlight_extremes=highlight_extremes,
        show_period_pct=show_period_pct,
    )
    st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)

    buffer = io.StringIO()
    fig.write_html(buffer, full_html=False)
    buffer.seek(0)
    st.download_button(
        label="Download Plotly Trend as HTML",
        data=buffer.getvalue(),
        file_name="net_worth_over_time.html",
        mime="text/html",
    )

    latest_mix = (
        agg_df[agg_df[period_str_col] == totals_df.iloc[-1][period_str_col]]
        .sort_values(ColumnNames.AMOUNT, ascending=False)
        .rename(columns={color_column: legend_title, ColumnNames.AMOUNT: "Current Balance"})
    )
    with st.expander("Latest Composition Table", expanded=False):
        st.dataframe(latest_mix[[legend_title, "Current Balance"]], width="stretch", hide_index=True)


def show_growth_over_time(filtered_df: pd.DataFrame) -> None:
    """Display the redesigned net worth trend experience."""
    inject_surface_styles()
    render_page_hero(
        "Net Worth",
        "Trend",
        "Track the shape of net worth over time, then switch views for drivers or composition.",
        "Overview shows the trend, Drivers ranks movers, and Composition shows the full breakdown.",
    )

    if filtered_df.empty:
        st.warning("No data available. Please adjust your filters.")
        return

    base_totals_df = filtered_df.groupby([ColumnNames.MONTH, ColumnNames.MONTH_STR], as_index=False)[ColumnNames.AMOUNT].sum()
    if len(base_totals_df) < 2:
        st.warning("Need at least 2 months of data for analysis.")
        return

    render_section_intro(
        "Snapshot",
        "A quick read on balance, growth, pace, and history depth.",
    )
    _render_summary_cards(base_totals_df)

    st.divider()
    render_section_intro(
        "Analysis",
        "Choose the view first, then refine the lens only when needed.",
    )

    view_col, breakdown_col, period_col_ui, preset_col, settings_col = st.columns([1.4, 1.3, 1.1, 1.2, 0.8])
    with view_col:
        view_mode = st.radio("View", VIEW_MODES, index=0, horizontal=True)
    with breakdown_col:
        breakdown_by = st.selectbox("Breakdown", list(BREAKDOWN_LABELS.values()), index=0)
    with period_col_ui:
        period_comparison = st.selectbox("Period View", PERIOD_OPTIONS, index=0)
    with preset_col:
        view_preset = st.selectbox("Overlay Style", VIEW_PRESETS, index=1)
    with settings_col:
        with st.popover("Options"):
            show_period_pct = st.checkbox("Show % change", value=True)
            highlight_extremes = st.checkbox("Highlight best / worst", value=False)
            show_milestones = st.checkbox("Show milestone guides", value=False)

    show_trend_line = view_preset == "With Trend Line"
    show_rolling_avg = view_preset == "With 3-month Average" and period_comparison == "Monthly"

    period_filtered_df, period_col, period_str_col = _prepare_period_data(filtered_df, period_comparison)
    breakdown_key = next(key for key, value in BREAKDOWN_LABELS.items() if value == breakdown_by)
    agg_df, color_column, legend_title = _aggregate_trend_data(
        period_filtered_df=period_filtered_df,
        breakdown_key=breakdown_key,
        period_col=period_col,
        period_str_col=period_str_col,
    )
    totals_df = _build_totals_df(agg_df, period_col, period_str_col, show_rolling_avg)

    if view_mode == "Overview":
        _render_overview_mode(
            period_filtered_df=period_filtered_df,
            agg_df=agg_df,
            totals_df=totals_df,
            period_col=period_col,
            period_str_col=period_str_col,
            color_column=color_column,
            legend_title=legend_title,
            period_comparison=period_comparison,
            show_trend_line=show_trend_line,
            show_rolling_avg=show_rolling_avg,
            show_milestones=show_milestones,
            highlight_extremes=highlight_extremes,
            show_period_pct=show_period_pct,
        )
    elif view_mode == "Drivers":
        _render_drivers_mode(agg_df=agg_df, color_column=color_column, legend_title=legend_title)
    elif view_mode == "Composition":
        _render_composition_mode(
            agg_df=agg_df,
            totals_df=totals_df,
            period_col=period_col,
            period_str_col=period_str_col,
            color_column=color_column,
            legend_title=legend_title,
            period_comparison=period_comparison,
            show_trend_line=show_trend_line,
            show_rolling_avg=show_rolling_avg,
            show_milestones=show_milestones,
            highlight_extremes=highlight_extremes,
            show_period_pct=show_period_pct,
        )
