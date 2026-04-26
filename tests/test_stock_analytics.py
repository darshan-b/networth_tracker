import math

import pandas as pd

from data.stock_analytics import (
    build_cash_flow_snapshot,
    calculate_portfolio_overview_metrics,
    calculate_time_weighted_returns,
    calculate_xirr,
)


def test_time_weighted_returns_remove_same_day_contributions() -> None:
    portfolio_daily = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "Current Value": [100.0, 210.0, 220.0],
            "Cost Basis": [100.0, 200.0, 200.0],
        }
    )
    cash_flows = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02"]),
            "net_contribution": [100.0],
            "income_received": [0.0],
        }
    )

    twr = calculate_time_weighted_returns(portfolio_daily, cash_flows)

    assert math.isclose(twr.loc[1, "Flow Adjusted Return"], 0.10, rel_tol=1e-9)
    assert math.isclose(twr.loc[2, "Flow Adjusted Cumulative Return"], 0.15238095238095228, rel_tol=1e-9)


def test_xirr_returns_zero_when_cash_flows_do_not_bracket_solution() -> None:
    cash_flows = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01"]),
            "investor_cash_flow": [-100.0],
        }
    )

    assert calculate_xirr(cash_flows, ending_value=0.0) == 0.0


def test_overview_metrics_separate_investment_and_personal_return() -> None:
    historical = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "quantity": [1.0, 2.0, 2.0],
            "Brokerage": ["Fidelity", "Fidelity", "Fidelity"],
            "Account Name": ["Taxable", "Taxable", "Taxable"],
            "Investment Type": ["Stock", "Stock", "Stock"],
            "Current Value": [100.0, 210.0, 220.0],
            "Cost Basis": [100.0, 200.0, 200.0],
            "Total Gain/Loss": [0.0, 10.0, 20.0],
            "Total Gain/Loss %": [0.0, 5.0, 10.0],
            "Last Close": [100.0, 105.0, 110.0],
        }
    )
    trading_log = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02"]),
            "ticker": ["AAPL"],
            "Brokerage": ["Fidelity"],
            "Account Name": ["Taxable"],
            "Investment Type": ["Stock"],
            "Transaction Type": ["Buy"],
            "Amount": [100.0],
            "Quantity": [1.0],
        }
    )

    metrics = calculate_portfolio_overview_metrics(historical, trading_log)

    assert math.isclose(metrics["investment_return"], 0.15238095238095228, rel_tol=1e-9)
    assert metrics["net_contributions"] == 100.0
    assert math.isclose(metrics["personal_return"], 0.13333333333333333, rel_tol=1e-9)


def test_build_cash_flow_snapshot_tracks_income_and_contributions() -> None:
    trading_log = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"]),
            "Transaction Type": ["Buy", "Sell", "Dividend"],
            "Amount": [100.0, 40.0, 5.0],
        }
    )

    snapshot = build_cash_flow_snapshot(trading_log)

    assert snapshot.net_contributions == 60.0
    assert snapshot.income_received == 5.0
    assert snapshot.buys == 100.0
    assert snapshot.sells == 40.0
