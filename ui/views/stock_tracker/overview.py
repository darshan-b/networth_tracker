"""Overview tab for stock portfolio analysis."""

from datetime import datetime, timedelta
from typing import List

import pandas as pd
import streamlit as st

from data.stock_analytics import calculate_portfolio_overview_metrics
from ui.charts import create_cost_basis_comparison
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_metric_card,
    render_page_hero,
    render_section_intro,
)


def get_date_range(period: str, end_date: datetime) -> datetime | None:
    """Calculate the start date for a given overview period."""
    period_map = {
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "3Y": 1095,
    }

    if period == "YTD":
        return datetime(end_date.year, 1, 1)
    if period == "All":
        return None
    return end_date - timedelta(days=period_map.get(period, 0))


def render(
    historical_df: pd.DataFrame,
    selected_symbols: List[str],
    trading_log: pd.DataFrame,
) -> None:
    """Render the portfolio overview tab."""
    try:
        inject_surface_styles()
        render_page_hero(
            "Stocks",
            "Overview",
            "Review the current filtered portfolio, contribution context, and period movement.",
            "Holdings stay brokerage/account aware so duplicate tickers do not collapse into one row.",
        )

        if historical_df.empty:
            st.warning("No historical tracking data available for selected filters.")
            return

        _render_time_range_selector()
        time_range = st.session_state.get("time_range", "All")
        historical_filtered = _apply_time_filter(historical_df, time_range)
        trading_filtered = _apply_time_filter(trading_log, time_range) if trading_log is not None and not trading_log.empty else pd.DataFrame()

        if historical_filtered.empty:
            st.warning(f"No data available for the selected time range ({time_range}).")
            return

        metrics = calculate_portfolio_overview_metrics(historical_filtered, trading_filtered)
        snapshot = metrics["snapshot"]
        latest_data = snapshot.latest_positions
        start_data = snapshot.start_positions

        if latest_data.empty:
            st.info("No positions found for the selected period.")
            return

        render_section_intro(
            "Snapshot",
            "Use these cards to separate holding-level unrealized P/L from flow-adjusted investment performance and money-weighted personal return.",
        )
        _render_primary_metric_cards(metrics, time_range)

        render_section_intro(
            "Return Quality",
            "These stats summarize the filtered portfolio the way a mature portfolio product would: path-dependent return, volatility, downside, drawdown, and concentration.",
        )
        _render_secondary_metric_cards(metrics, latest_data)

        st.divider()
        render_section_intro(
            "Portfolio Analysis",
            "Track how the filtered portfolio value evolved against total cost basis over the selected period.",
        )
        fig = create_cost_basis_comparison(snapshot.active_history)
        if fig:
            st.plotly_chart(fig, config={"responsive": True})
        else:
            st.info("Unable to create performance comparison chart.")

        render_section_intro(
            "Current Holdings",
            "Latest active positions for the current filter set, kept separate by brokerage and account.",
        )
        _render_holdings_table(latest_data, start_data, time_range)

        if selected_symbols:
            render_accent_pills(
                [
                    ("Selected Symbols", str(len(selected_symbols))),
                    ("Active Positions", str(len(latest_data))),
                    ("Accounts", str(latest_data["Account Name"].nunique())),
                    ("Brokerages", str(latest_data["Brokerage"].nunique())),
                ]
            )

    except Exception as e:
        st.error(f"Error rendering overview: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_time_range_selector() -> None:
    """Render time range selection radio buttons."""
    col1, _, _ = st.columns([2, 1, 1])
    with col1:
        st.radio(
            "Time Range",
            options=["1M", "3M", "6M", "YTD", "1Y", "3Y", "All"],
            index=6,
            horizontal=True,
            key="time_range",
        )


def _apply_time_filter(df: pd.DataFrame, time_range: str) -> pd.DataFrame:
    """Apply the overview time range filter."""
    if df is None or df.empty or "Date" not in df.columns:
        return df.copy() if df is not None else pd.DataFrame()
    end_date = df["Date"].max()
    start_date = get_date_range(time_range, end_date)
    if start_date is None:
        return df.copy()
    return df[df["Date"] >= start_date].copy()


def _render_primary_metric_cards(metrics: dict, time_range: str) -> None:
    """Render the top-line overview cards."""
    total_gain = metrics["total_gain_loss"]
    total_gain_pct = metrics["total_gain_loss_pct"] * 100
    investment_return = metrics["investment_return"] * 100
    annualized_investment_return = metrics["annualized_investment_return"] * 100
    personal_return = metrics["personal_return"] * 100

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        render_metric_card(
            "Total Value",
            f"${metrics['total_value']:,.0f}",
            "Latest snapshot",
            "Current market value across the filtered active positions.",
            "positive",
        )

    with col2:
        render_metric_card(
            "Total Cost Basis",
            f"${metrics['total_cost']:,.0f}",
            "Capital at work",
            "Remaining cost basis for the filtered active positions.",
            "neutral",
        )

    with col3:
        render_metric_card(
            "Total Gain/Loss",
            f"${total_gain:,.0f}",
            f"{total_gain_pct:.2f}%",
            "Unrealized gain/loss on the filtered active portfolio.",
            "positive" if total_gain > 0 else "negative" if total_gain < 0 else "neutral",
        )

    with col4:
        render_metric_card(
            f"Investment Return ({time_range})",
            f"{investment_return:.2f}%",
            "Flow adjusted",
            "Time-weighted style return that removes buy and sell cash flows from the selected period.",
            "positive" if investment_return > 0 else "negative" if investment_return < 0 else "neutral",
        )

    with col5:
        render_metric_card(
            "Personal Return",
            f"{personal_return:.2f}%",
            "Money weighted",
            "XIRR-style personal return that reflects the timing of your contributions and withdrawals.",
            "positive" if personal_return > 0 else "negative" if personal_return < 0 else "neutral",
        )


def _render_secondary_metric_cards(metrics: dict, latest_data: pd.DataFrame) -> None:
    """Render deeper return-quality and concentration cards."""
    stats = metrics["stats"]
    concentration = metrics["concentration"]
    annualized_investment_return = metrics["annualized_investment_return"] * 100
    start_date = pd.to_datetime(metrics["start_date"]) if pd.notna(metrics["start_date"]) else pd.NaT
    end_date = pd.to_datetime(metrics["end_date"]) if pd.notna(metrics["end_date"]) else pd.NaT
    period_days = max((end_date - start_date).days, 0) if pd.notna(start_date) and pd.notna(end_date) else 0
    annualized_label = "Annualized Investment Return" if period_days >= 365 else "Extrapolated Annualized Return"
    portfolio_drawdown = (
        metrics["snapshot"].portfolio_daily["Drawdown"].min() * 100
        if not metrics["snapshot"].portfolio_daily.empty
        else 0.0
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            "Sharpe Ratio",
            f"{stats['sharpe_ratio']:.2f}",
            "Risk-adjusted return",
            "Uses daily returns and assumes a 0% risk-free rate.",
            "positive" if stats["sharpe_ratio"] > 0 else "negative" if stats["sharpe_ratio"] < 0 else "neutral",
        )

    with col2:
        render_metric_card(
            "Sortino Ratio",
            f"{stats['sortino_ratio']:.2f}",
            "Downside aware",
            "Rewards return while penalizing downside volatility only.",
            "positive" if stats["sortino_ratio"] > 0 else "negative" if stats["sortino_ratio"] < 0 else "neutral",
        )

    with col3:
        render_metric_card(
            "Annualized Volatility",
            f"{stats['annualized_volatility'] * 100:.2f}%",
            "Daily return based",
            "Standard deviation of daily returns annualized to 252 trading days.",
            "negative",
        )

    with col4:
        render_metric_card(
            "Max Drawdown",
            f"{portfolio_drawdown:.2f}%",
            "Peak to trough",
            "Largest decline from a prior high during the selected range.",
            "negative" if portfolio_drawdown < 0 else "neutral",
        )

    render_accent_pills(
        [
            (annualized_label, f"{annualized_investment_return:.2f}%"),
            ("Win Rate", f"{stats['win_rate'] * 100:.1f}%"),
            ("Best Day", f"{stats['best_day'] * 100:.2f}%"),
            ("Worst Day", f"{stats['worst_day'] * 100:.2f}%"),
            ("VaR 95%", f"{stats['value_at_risk_95'] * 100:.2f}%"),
            ("Net Contributions", f"${metrics['net_contributions']:,.0f}"),
            ("Income Received", f"${metrics['income_received']:,.0f}"),
            ("Largest Position", f"{concentration['largest_position_weight'] * 100:.1f}%"),
            ("Top 3 Weight", f"{concentration['top_3_weight'] * 100:.1f}%"),
            ("Symbols", str(concentration['symbol_count'])),
            ("Positions", str(concentration['position_count'])),
            ("Accounts", str(latest_data["Account Name"].nunique())),
        ]
    )


def _render_holdings_table(
    latest_data: pd.DataFrame,
    start_data: pd.DataFrame,
    time_range: str,
) -> None:
    """Render holdings table with detailed position information."""
    holdings_display = latest_data.copy()
    if holdings_display.empty:
        st.info("No holdings to display for the selected period.")
        return

    holdings_display["Avg Cost"] = holdings_display["Cost Basis"] / holdings_display["quantity"].replace(0, pd.NA)
    holdings_display = holdings_display.merge(
        start_data[["position_key", "Current Value"]],
        on="position_key",
        how="left",
        suffixes=("", "_start"),
    )

    holdings_display["Period Return %"] = holdings_display.apply(
        lambda row: (
            (row["Current Value"] / row["Current Value_start"] - 1) * 100
            if pd.notna(row["Current Value_start"]) and row["Current Value_start"] > 0
            else 0.0
        ),
        axis=1,
    )

    required_columns = [
        "Brokerage",
        "ticker",
        "Account Name",
        "quantity",
        "Avg Cost",
        "Last Close",
        "Current Value",
        "Cost Basis",
        "Total Gain/Loss",
        "Total Gain/Loss %",
        "Period Return %",
    ]
    missing_columns = [col for col in required_columns if col not in holdings_display.columns]
    if missing_columns:
        st.error(
            "Unable to render holdings table because these columns are missing: "
            + ", ".join(missing_columns)
        )
        return

    holdings_display = holdings_display[required_columns].copy().rename(
        columns={
            "ticker": "Ticker",
            "Account Name": "Account",
            "quantity": "Quantity",
            "Last Close": "Last Price",
            "Current Value": "Current Value",
            "Cost Basis": "Cost Basis",
            "Total Gain/Loss": "Gain/Loss ($)",
            "Total Gain/Loss %": "Gain/Loss (%)",
            "Period Return %": f"{time_range} Return (%)",
        }
    )

    st.dataframe(
        holdings_display.style.format(
            {
                "Quantity": "{:.3f}",
                "Avg Cost": "${:.2f}",
                "Last Price": "${:.2f}",
                "Current Value": "${:,.2f}",
                "Cost Basis": "${:,.2f}",
                "Gain/Loss ($)": "${:,.2f}",
                "Gain/Loss (%)": "{:.2f}%",
                f"{time_range} Return (%)": "{:.2f}%",
            }
        ).background_gradient(
            subset=["Gain/Loss (%)"],
            cmap="RdYlGn",
            vmin=-20,
            vmax=20,
        ),
        width="stretch",
        height=420,
        hide_index=True,
    )
