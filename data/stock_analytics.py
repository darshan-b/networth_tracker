"""Shared stock analytics helpers used across portfolio views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from app_constants import StockColumnNames

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Position-aware snapshot data for the active filtered portfolio."""

    latest_positions: pd.DataFrame
    active_history: pd.DataFrame
    start_positions: pd.DataFrame
    portfolio_daily: pd.DataFrame


@dataclass(frozen=True)
class CashFlowSnapshot:
    """Cash-flow series derived from the trading log."""

    daily_flows: pd.DataFrame
    net_contributions: float
    income_received: float
    buys: float
    sells: float


def normalize_label_series(series: pd.Series) -> pd.Series:
    """Normalize free-text labels so joins and filters survive formatting drift."""
    return series.fillna("").astype(str).str.strip().str.casefold()


def build_position_key(df: pd.DataFrame) -> pd.Series:
    """Build a stable brokerage/account/ticker key for position-aware analysis."""
    return (
        normalize_label_series(df[StockColumnNames.BROKERAGE])
        + "||"
        + normalize_label_series(df[StockColumnNames.ACCOUNT_NAME])
        + "||"
        + normalize_label_series(df[StockColumnNames.TICKER])
    )


def with_position_key(df: pd.DataFrame) -> pd.DataFrame:
    """Attach a position key to a copy of the input frame."""
    keyed = df.copy()
    keyed["position_key"] = build_position_key(keyed)
    return keyed


def get_latest_positions(historical_df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest snapshot for each brokerage/account/ticker position."""
    if historical_df is None or historical_df.empty:
        return pd.DataFrame()

    keyed = with_position_key(historical_df)
    return (
        keyed.sort_values(StockColumnNames.DATE)
        .groupby("position_key", as_index=False)
        .last()
    )


def get_active_latest_positions(historical_df: pd.DataFrame) -> pd.DataFrame:
    """Return latest positions that still have a positive quantity."""
    latest_positions = get_latest_positions(historical_df)
    if latest_positions.empty or StockColumnNames.QUANTITY not in latest_positions.columns:
        return pd.DataFrame()
    return latest_positions[latest_positions[StockColumnNames.QUANTITY] > 0].copy()


def get_active_position_keys(historical_df: pd.DataFrame) -> list[str]:
    """Return active brokerage/account/ticker position keys."""
    latest_positions = get_active_latest_positions(historical_df)
    if latest_positions.empty:
        return []
    return latest_positions["position_key"].tolist()


def get_filtered_symbols(historical_df: pd.DataFrame) -> list[str]:
    """Return currently owned symbols from a filtered historical frame."""
    latest_positions = get_active_latest_positions(historical_df)
    if latest_positions.empty:
        return []
    return sorted(latest_positions[StockColumnNames.TICKER].dropna().astype(str).unique().tolist())


def build_portfolio_snapshot(historical_df: pd.DataFrame) -> PortfolioSnapshot:
    """Build the active holdings snapshot and portfolio-daily series."""
    latest_positions = get_active_latest_positions(historical_df)
    if latest_positions.empty:
        empty = pd.DataFrame()
        return PortfolioSnapshot(empty, empty, empty, empty)

    active_keys = latest_positions["position_key"].tolist()
    active_history = with_position_key(historical_df)
    active_history = active_history[active_history["position_key"].isin(active_keys)].copy()

    start_positions = (
        active_history.sort_values(StockColumnNames.DATE)
        .groupby("position_key", as_index=False)
        .first()
    )

    portfolio_daily = aggregate_portfolio_daily(active_history)
    return PortfolioSnapshot(latest_positions, active_history, start_positions, portfolio_daily)


def aggregate_portfolio_daily(historical_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the active filtered portfolio to one row per day."""
    if historical_df is None or historical_df.empty:
        return pd.DataFrame()

    aggregation: dict[str, str] = {
        "Current Value": "sum",
        "Cost Basis": "sum",
    }
    if "Total Gain/Loss" in historical_df.columns:
        aggregation["Total Gain/Loss"] = "sum"

    daily = (
        historical_df.groupby(StockColumnNames.DATE, as_index=False)
        .agg(aggregation)
        .sort_values(StockColumnNames.DATE)
        .reset_index(drop=True)
    )

    daily["Daily Return"] = daily["Current Value"].pct_change()
    daily["Cumulative Return"] = (1 + daily["Daily Return"].fillna(0)).cumprod() - 1
    daily["Running Max"] = daily["Current Value"].cummax()
    daily["Drawdown"] = np.where(
        daily["Running Max"] > 0,
        daily["Current Value"] / daily["Running Max"] - 1,
        0.0,
    )
    return daily


def _get_transaction_type_series(trading_log: pd.DataFrame) -> pd.Series:
    """Return normalized transaction types."""
    if "Transaction Type" not in trading_log.columns:
        return pd.Series("", index=trading_log.index, dtype="object")
    return trading_log["Transaction Type"].fillna("").astype(str).str.strip().str.casefold()


def _classify_transaction_flows(trading_log: pd.DataFrame) -> pd.DataFrame:
    """Map trading log rows into contribution and income buckets."""
    if trading_log is None or trading_log.empty or "Amount" not in trading_log.columns:
        return pd.DataFrame(columns=["Date", "net_contribution", "income_received", "investor_cash_flow"])

    classified = trading_log.copy()
    if StockColumnNames.DATE not in classified.columns:
        return pd.DataFrame(columns=["Date", "net_contribution", "income_received", "investor_cash_flow"])

    classified[StockColumnNames.DATE] = pd.to_datetime(classified[StockColumnNames.DATE], errors="coerce")
    classified = classified.dropna(subset=[StockColumnNames.DATE]).copy()
    if classified.empty:
        return pd.DataFrame(columns=["Date", "net_contribution", "income_received", "investor_cash_flow"])

    amount_series = pd.to_numeric(classified["Amount"], errors="coerce").fillna(0.0)
    type_series = _get_transaction_type_series(classified)

    buy_mask = type_series.eq("buy")
    sell_mask = type_series.eq("sell")
    income_mask = type_series.str.contains("dividend|distribution|interest|credit", regex=True)

    classified["net_contribution"] = 0.0
    classified.loc[buy_mask, "net_contribution"] = amount_series.loc[buy_mask]
    classified.loc[sell_mask, "net_contribution"] = -amount_series.loc[sell_mask]

    classified["income_received"] = 0.0
    classified.loc[income_mask, "income_received"] = amount_series.loc[income_mask].clip(lower=0.0)

    classified["investor_cash_flow"] = 0.0
    classified.loc[buy_mask, "investor_cash_flow"] = -amount_series.loc[buy_mask]
    classified.loc[sell_mask, "investor_cash_flow"] = amount_series.loc[sell_mask]
    classified.loc[income_mask, "investor_cash_flow"] += amount_series.loc[income_mask].clip(lower=0.0)

    return (
        classified.groupby(StockColumnNames.DATE, as_index=False)[
            ["net_contribution", "income_received", "investor_cash_flow"]
        ]
        .sum()
        .sort_values(StockColumnNames.DATE)
        .reset_index(drop=True)
    )


def build_cash_flow_snapshot(trading_log: Optional[pd.DataFrame]) -> CashFlowSnapshot:
    """Aggregate contribution and income flows from the filtered trading log."""
    if trading_log is None or trading_log.empty:
        empty = pd.DataFrame(columns=["Date", "net_contribution", "income_received", "investor_cash_flow"])
        return CashFlowSnapshot(empty, 0.0, 0.0, 0.0, 0.0)

    daily_flows = _classify_transaction_flows(trading_log)
    type_series = _get_transaction_type_series(trading_log)
    amount_series = pd.to_numeric(trading_log["Amount"], errors="coerce").fillna(0.0) if "Amount" in trading_log.columns else pd.Series(0.0, index=trading_log.index)
    buys = float(amount_series[type_series.eq("buy")].sum())
    sells = float(amount_series[type_series.eq("sell")].sum())
    income_received = float(daily_flows["income_received"].sum()) if not daily_flows.empty else 0.0
    net_contributions = float(daily_flows["net_contribution"].sum()) if not daily_flows.empty else 0.0
    return CashFlowSnapshot(daily_flows, net_contributions, income_received, buys, sells)


def calculate_time_weighted_returns(
    portfolio_daily: pd.DataFrame,
    cash_flows: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Calculate flow-adjusted daily returns for the portfolio.

    Assumption: market value is end-of-day, and same-day buys/sells are external capital flows.
    Dividend/distribution cash is treated as return, not as contribution.
    """
    if portfolio_daily is None or portfolio_daily.empty:
        return pd.DataFrame()

    twr = portfolio_daily.copy()
    merge_columns = [StockColumnNames.DATE, "net_contribution", "income_received"]
    if cash_flows is None or cash_flows.empty:
        twr["net_contribution"] = 0.0
        twr["income_received"] = 0.0
    else:
        twr = twr.merge(cash_flows[merge_columns], on=StockColumnNames.DATE, how="left")
        twr["net_contribution"] = twr["net_contribution"].fillna(0.0)
        twr["income_received"] = twr["income_received"].fillna(0.0)

    prior_value = twr["Current Value"].shift(1)
    twr["Flow Adjusted Return"] = np.where(
        prior_value > 0,
        (
            twr["Current Value"]
            - prior_value
            - twr["net_contribution"]
            + twr["income_received"]
        ) / prior_value,
        np.nan,
    )
    twr["Flow Adjusted Cumulative Return"] = (
        1 + twr["Flow Adjusted Return"].fillna(0.0)
    ).cumprod() - 1
    return twr


def aggregate_symbol_history(historical_df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Aggregate one clean daily symbol series across brokerages/accounts."""
    if historical_df is None or historical_df.empty:
        return pd.DataFrame()

    symbol_data = historical_df[historical_df[StockColumnNames.TICKER] == symbol].copy()
    if symbol_data.empty:
        return symbol_data

    aggregation: dict[str, str] = {
        "Current Value": "sum",
        "Cost Basis": "sum",
    }
    if "Last Close" in symbol_data.columns:
        aggregation["Last Close"] = "mean"
    if "Total Gain/Loss" in symbol_data.columns:
        aggregation["Total Gain/Loss"] = "sum"

    aggregated = (
        symbol_data.groupby(StockColumnNames.DATE, as_index=False)
        .agg(aggregation)
        .sort_values(StockColumnNames.DATE)
        .reset_index(drop=True)
    )

    if "Last Close" in aggregated.columns:
        aggregated["Daily Return"] = aggregated["Last Close"].pct_change()
        aggregated["Running Max"] = aggregated["Last Close"].cummax()
        aggregated["Drawdown"] = np.where(
            aggregated["Running Max"] > 0,
            aggregated["Last Close"] / aggregated["Running Max"] - 1,
            0.0,
        )
    else:
        aggregated["Daily Return"] = aggregated["Current Value"].pct_change()
        aggregated["Running Max"] = aggregated["Current Value"].cummax()
        aggregated["Drawdown"] = np.where(
            aggregated["Running Max"] > 0,
            aggregated["Current Value"] / aggregated["Running Max"] - 1,
            0.0,
        )

    return aggregated


def calculate_annualized_return(
    start_value: float,
    end_value: float,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> float:
    """Calculate CAGR-style annualized return for the observed date span."""
    if start_value <= 0 or end_value <= 0 or pd.isna(start_date) or pd.isna(end_date):
        return 0.0

    days = max((pd.to_datetime(end_date) - pd.to_datetime(start_date)).days, 0)
    years = days / 365.25
    if years <= 0:
        return 0.0

    return (end_value / start_value) ** (1 / years) - 1


def calculate_annualized_return_from_series(
    cumulative_return: float,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> float:
    """Annualize a cumulative return over the observed date span."""
    if pd.isna(start_date) or pd.isna(end_date):
        return 0.0
    days = max((pd.to_datetime(end_date) - pd.to_datetime(start_date)).days, 0)
    years = days / 365.25
    if years <= 0:
        return 0.0
    return (1 + cumulative_return) ** (1 / years) - 1 if cumulative_return > -1 else -1.0


def calculate_xirr(
    cash_flows: pd.DataFrame,
    ending_value: float,
    ending_date: Optional[pd.Timestamp] = None,
) -> float:
    """Calculate money-weighted return using irregular cash flows."""
    if cash_flows is None or cash_flows.empty or ending_value <= 0:
        return 0.0

    flows = cash_flows[[StockColumnNames.DATE, "investor_cash_flow"]].copy()
    flows = flows.rename(columns={"investor_cash_flow": "cash_flow"})
    flows = flows[flows["cash_flow"] != 0].copy()
    if flows.empty:
        return 0.0

    terminal_date = pd.to_datetime(ending_date) if ending_date is not None else pd.to_datetime(flows[StockColumnNames.DATE].max())
    flows.loc[len(flows)] = {
        StockColumnNames.DATE: terminal_date,
        "cash_flow": float(ending_value),
    }
    flows = flows.sort_values(StockColumnNames.DATE).reset_index(drop=True)

    if not ((flows["cash_flow"] < 0).any() and (flows["cash_flow"] > 0).any()):
        return 0.0

    base_date = pd.to_datetime(flows.loc[0, StockColumnNames.DATE])
    year_fractions = (
        (pd.to_datetime(flows[StockColumnNames.DATE]) - base_date).dt.days / 365.25
    )
    cash_values = flows["cash_flow"].astype(float).to_numpy()
    time_values = year_fractions.astype(float).to_numpy()

    def npv(rate: float) -> float:
        return float(np.sum(cash_values / np.power(1 + rate, time_values)))

    low, high = -0.9999, 10.0
    low_value = npv(low)
    high_value = npv(high)
    if np.isnan(low_value) or np.isnan(high_value):
        return 0.0

    expansion_count = 0
    while low_value * high_value > 0 and expansion_count < 12:
        high *= 2
        high_value = npv(high)
        expansion_count += 1

    if low_value * high_value > 0:
        return 0.0

    for _ in range(100):
        mid = (low + high) / 2
        mid_value = npv(mid)
        if abs(mid_value) < 1e-8:
            return float(mid)
        if low_value * mid_value <= 0:
            high = mid
            high_value = mid_value
        else:
            low = mid
            low_value = mid_value

    return float((low + high) / 2)


def calculate_modified_dietz_return(
    cash_flows: pd.DataFrame,
    start_value: float,
    end_value: float,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> float:
    """Calculate a money-weighted return for the period using Modified Dietz."""
    if start_value < 0 or end_value < 0 or pd.isna(start_date) or pd.isna(end_date):
        return 0.0

    period_days = max((pd.to_datetime(end_date) - pd.to_datetime(start_date)).days, 0)
    if period_days == 0:
        return 0.0

    if cash_flows is None or cash_flows.empty:
        denominator = start_value
        numerator = end_value - start_value
        return numerator / denominator if denominator > 0 else 0.0

    flows = cash_flows[[StockColumnNames.DATE, "net_contribution"]].copy()
    flows = flows[flows["net_contribution"] != 0].copy()
    if flows.empty:
        denominator = start_value
        numerator = end_value - start_value
        return numerator / denominator if denominator > 0 else 0.0

    flow_days = (pd.to_datetime(end_date) - pd.to_datetime(flows[StockColumnNames.DATE])).dt.days.clip(lower=0)
    weights = flow_days / period_days
    weighted_flows = float((flows["net_contribution"] * weights).sum())
    total_flows = float(flows["net_contribution"].sum())

    denominator = start_value + weighted_flows
    numerator = end_value - start_value - total_flows
    return numerator / denominator if denominator > 0 else 0.0


def calculate_return_statistics(
    returns: pd.Series,
    annualization_factor: int = TRADING_DAYS_PER_YEAR,
) -> dict[str, float]:
    """Calculate common mature-product return statistics from a return series."""
    clean_returns = pd.to_numeric(returns, errors="coerce").dropna()
    if clean_returns.empty:
        return {
            "avg_daily_return": 0.0,
            "volatility": 0.0,
            "downside_deviation": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "win_rate": 0.0,
            "best_day": 0.0,
            "worst_day": 0.0,
            "value_at_risk_95": 0.0,
        }

    avg_daily_return = float(clean_returns.mean())
    volatility = float(clean_returns.std())
    annualized_volatility = volatility * np.sqrt(annualization_factor)
    annualized_return = avg_daily_return * annualization_factor
    downside = clean_returns[clean_returns < 0]
    downside_deviation = float(downside.std()) if not downside.empty else 0.0
    annualized_downside = downside_deviation * np.sqrt(annualization_factor)

    return {
        "avg_daily_return": avg_daily_return,
        "volatility": volatility,
        "downside_deviation": downside_deviation,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": annualized_return / annualized_volatility if annualized_volatility > 0 else 0.0,
        "sortino_ratio": annualized_return / annualized_downside if annualized_downside > 0 else 0.0,
        "win_rate": float((clean_returns > 0).mean()),
        "best_day": float(clean_returns.max()),
        "worst_day": float(clean_returns.min()),
        "value_at_risk_95": float(clean_returns.quantile(0.05)),
    }


def calculate_max_drawdown(drawdown_series: pd.Series) -> float:
    """Return the deepest drawdown from a drawdown series."""
    clean_drawdown = pd.to_numeric(drawdown_series, errors="coerce").dropna()
    if clean_drawdown.empty:
        return 0.0
    return float(clean_drawdown.min())


def calculate_concentration(latest_positions: pd.DataFrame) -> dict[str, float]:
    """Calculate concentration metrics for active latest positions."""
    if latest_positions is None or latest_positions.empty:
        return {
            "largest_position_weight": 0.0,
            "top_3_weight": 0.0,
            "position_count": 0,
            "symbol_count": 0,
        }

    total_value = latest_positions["Current Value"].sum()
    if total_value <= 0:
        weights = pd.Series(0.0, index=latest_positions.index)
    else:
        weights = latest_positions["Current Value"] / total_value

    return {
        "largest_position_weight": float(weights.max()) if not weights.empty else 0.0,
        "top_3_weight": float(weights.sort_values(ascending=False).head(3).sum()),
        "position_count": int(len(latest_positions)),
        "symbol_count": int(latest_positions[StockColumnNames.TICKER].nunique()),
    }


def calculate_portfolio_overview_metrics(
    historical_df: pd.DataFrame,
    trading_log: Optional[pd.DataFrame] = None,
) -> dict[str, object]:
    """Calculate the primary snapshot and return metrics for the overview page."""
    snapshot = build_portfolio_snapshot(historical_df)
    if snapshot.latest_positions.empty:
        return {
            "snapshot": snapshot,
            "total_value": 0.0,
            "total_cost": 0.0,
            "total_gain_loss": 0.0,
            "total_gain_loss_pct": 0.0,
            "investment_return": 0.0,
            "annualized_investment_return": 0.0,
            "personal_return": 0.0,
            "net_contributions": 0.0,
            "income_received": 0.0,
            "start_date": pd.NaT,
            "end_date": pd.NaT,
            "stats": calculate_return_statistics(pd.Series(dtype=float)),
            "concentration": calculate_concentration(snapshot.latest_positions),
        }

    latest_positions = snapshot.latest_positions
    portfolio_daily = snapshot.portfolio_daily
    cash_flow_snapshot = build_cash_flow_snapshot(trading_log)
    twr_daily = calculate_time_weighted_returns(portfolio_daily, cash_flow_snapshot.daily_flows)

    total_value = float(latest_positions["Current Value"].sum())
    total_cost = float(latest_positions["Cost Basis"].sum())
    total_gain_loss = float(latest_positions["Total Gain/Loss"].sum()) if "Total Gain/Loss" in latest_positions.columns else total_value - total_cost
    total_gain_loss_pct = (total_gain_loss / total_cost) if total_cost > 0 else 0.0

    start_date = portfolio_daily[StockColumnNames.DATE].min() if not portfolio_daily.empty else pd.NaT
    end_date = portfolio_daily[StockColumnNames.DATE].max() if not portfolio_daily.empty else pd.NaT
    investment_return = (
        float(twr_daily["Flow Adjusted Cumulative Return"].iloc[-1])
        if not twr_daily.empty
        else 0.0
    )
    annualized_investment_return = calculate_annualized_return_from_series(
        investment_return,
        start_date,
        end_date,
    )
    start_value = float(portfolio_daily["Current Value"].iloc[0]) if not portfolio_daily.empty else 0.0
    personal_return = calculate_modified_dietz_return(
        cash_flow_snapshot.daily_flows,
        start_value,
        total_value,
        start_date,
        end_date,
    )

    return {
        "snapshot": snapshot,
        "total_value": total_value,
        "total_cost": total_cost,
        "total_gain_loss": total_gain_loss,
        "total_gain_loss_pct": total_gain_loss_pct,
        "investment_return": investment_return,
        "annualized_investment_return": annualized_investment_return,
        "personal_return": personal_return,
        "net_contributions": cash_flow_snapshot.net_contributions,
        "income_received": cash_flow_snapshot.income_received,
        "start_date": start_date,
        "end_date": end_date,
        "cash_flow_snapshot": cash_flow_snapshot,
        "twr_daily": twr_daily,
        "stats": calculate_return_statistics(twr_daily["Flow Adjusted Return"] if not twr_daily.empty else pd.Series(dtype=float)),
        "concentration": calculate_concentration(latest_positions),
    }
