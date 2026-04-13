"""Higher-level expense product insights and recommendations."""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

from app_constants import ColumnNames
from data.calculations import (
    calculate_category_spending,
    calculate_category_trends,
    calculate_monthly_cash_flow,
    calculate_net_outflow,
    is_expense_transaction,
    is_income_transaction,
)


class ChangeInsight(TypedDict):
    """Period-over-period cash-flow change summary."""

    current_month: pd.Timestamp
    previous_month: pd.Timestamp
    spending_delta: float
    spending_pct: float
    income_delta: float
    income_pct: float
    savings_delta: float
    savings_pct: float


class DriverInsight(TypedDict):
    """Largest category driver behind month-over-month change."""

    category: str
    delta: float


class SpendAnomaly(TypedDict):
    """Simple spending anomaly relative to typical day."""

    date: str
    amount: float
    multiple: float


class BudgetProjection(TypedDict):
    """Forward-looking budget pacing summary."""

    mode: str
    projected_spend_total: float
    projected_remaining_total: float
    at_risk_count: int
    lead_risk_category: str | None
    lead_risk_overage: float
    elapsed_days: int
    total_days: int


class BudgetRecommendation(TypedDict):
    """Actionable budget recommendation."""

    category: str
    status: str
    message: str


class RecurringMerchant(TypedDict):
    """Recurring merchant clue for transaction investigation."""

    merchant: str
    months_seen: int
    average_amount: float
    latest_amount: float


class DuplicateTransaction(TypedDict):
    """Potential duplicate transaction clue."""

    merchant: str
    date: str
    account: str
    amount: float
    duplicates: int


def get_month_over_month_change(df: pd.DataFrame) -> ChangeInsight | None:
    """Summarize the latest month-over-month change in cash flow."""
    cash_flow = calculate_monthly_cash_flow(df)
    if len(cash_flow) < 2:
        return None

    current = cash_flow.iloc[-1]
    previous = cash_flow.iloc[-2]
    spending_delta = float(current["expenses"] - previous["expenses"])
    income_delta = float(current["income"] - previous["income"])
    savings_delta = float(current["savings"] - previous["savings"])
    return {
        "current_month": current[ColumnNames.MONTH],
        "previous_month": previous[ColumnNames.MONTH],
        "spending_delta": spending_delta,
        "spending_pct": _pct_change(spending_delta, float(previous["expenses"])),
        "income_delta": income_delta,
        "income_pct": _pct_change(income_delta, float(previous["income"])),
        "savings_delta": savings_delta,
        "savings_pct": _pct_change(savings_delta, float(previous["savings"])),
    }


def get_top_change_driver(
    df: pd.DataFrame,
    current_month: pd.Timestamp | None = None,
    previous_month: pd.Timestamp | None = None,
) -> DriverInsight | None:
    """Return the category with the largest absolute spend change."""
    category_monthly = calculate_category_trends(df)
    if category_monthly.empty:
        return None

    if current_month is None or previous_month is None:
        months = sorted(category_monthly[ColumnNames.MONTH].dropna().unique())
        if len(months) < 2:
            return None
        previous_month = months[-2]
        current_month = months[-1]

    pivot = category_monthly[
        category_monthly[ColumnNames.MONTH].isin([current_month, previous_month])
    ].pivot_table(
        index=ColumnNames.CATEGORY,
        columns=ColumnNames.MONTH,
        values=ColumnNames.AMOUNT,
        fill_value=0.0,
    )
    if current_month not in pivot.columns or previous_month not in pivot.columns:
        return None

    delta = pivot[current_month] - pivot[previous_month]
    if delta.empty:
        return None

    category = str(delta.abs().idxmax())
    return {"category": category, "delta": float(delta.loc[category])}


def get_spend_anomaly(df: pd.DataFrame) -> SpendAnomaly | None:
    """Detect a simple daily spike relative to a typical spend day."""
    non_income_df = df[~is_income_transaction(df)].copy()
    if non_income_df.empty:
        return None

    daily_totals = (
        non_income_df.groupby(non_income_df[ColumnNames.DATE].dt.date)[ColumnNames.AMOUNT]
        .sum()
        .pipe(calculate_net_outflow)
    )
    if daily_totals.empty:
        return None

    median_day = float(daily_totals.median())
    peak_day = daily_totals.idxmax()
    peak_value = float(daily_totals.max())
    if median_day <= 0 or peak_value < median_day * 1.5:
        return None

    return {
        "date": peak_day.strftime("%b %d, %Y"),
        "amount": peak_value,
        "multiple": peak_value / median_day,
    }


def project_budget_outlook(
    df: pd.DataFrame,
    budget_df: pd.DataFrame,
    num_months: int,
) -> BudgetProjection | None:
    """Project budget outcomes for a single-month view, or return None otherwise."""
    if df.empty or budget_df.empty or num_months != 1:
        return None

    period_dates = pd.to_datetime(df[ColumnNames.DATE])
    latest_date = period_dates.max()
    earliest_date = period_dates.min()
    if latest_date.to_period("M") != earliest_date.to_period("M"):
        return None

    elapsed_days = max(int(latest_date.day), 1)
    total_days = int(latest_date.days_in_month)
    run_rate = total_days / elapsed_days

    projected_df = budget_df.copy()
    projected_df["ProjectedSpent"] = projected_df["Spent"] * run_rate
    projected_df["ProjectedOverage"] = projected_df["ProjectedSpent"] - projected_df["Budget"]
    at_risk = projected_df[projected_df["ProjectedOverage"] > 0].sort_values("ProjectedOverage", ascending=False)
    lead_risk = at_risk.iloc[0] if not at_risk.empty else None

    return {
        "mode": "projection",
        "projected_spend_total": float(projected_df["ProjectedSpent"].sum()),
        "projected_remaining_total": float(projected_df["Budget"].sum() - projected_df["ProjectedSpent"].sum()),
        "at_risk_count": int(len(at_risk)),
        "lead_risk_category": None if lead_risk is None else str(lead_risk[ColumnNames.CATEGORY]),
        "lead_risk_overage": 0.0 if lead_risk is None else float(lead_risk["ProjectedOverage"]),
        "elapsed_days": elapsed_days,
        "total_days": total_days,
    }


def get_budget_recommendations(budget_df: pd.DataFrame) -> list[BudgetRecommendation]:
    """Generate a small set of budget-focused recommendations."""
    if budget_df.empty:
        return []

    working_df = budget_df.sort_values("Percentage", ascending=False).copy()
    recommendations: list[BudgetRecommendation] = []
    for _, row in working_df.head(3).iterrows():
        category = str(row[ColumnNames.CATEGORY])
        pct = float(row["Percentage"])
        remaining = float(row["Remaining"])
        if pct > 100:
            recommendations.append({
                "category": category,
                "status": "negative",
                "message": f"{category} is already over budget by ${abs(remaining):,.0f}.",
            })
        elif pct > 85:
            recommendations.append({
                "category": category,
                "status": "neutral",
                "message": f"{category} has only ${remaining:,.0f} left and is close to budget.",
            })
    return recommendations


def get_recurring_merchants(df: pd.DataFrame, limit: int = 5) -> list[RecurringMerchant]:
    """Identify merchants that appear across multiple months with similar spend."""
    expense_df = df[is_expense_transaction(df)].copy()
    if expense_df.empty:
        return []

    expense_df[ColumnNames.MONTH] = expense_df[ColumnNames.DATE].dt.to_period("M").dt.to_timestamp()
    merchant_monthly = (
        expense_df.groupby([ColumnNames.MERCHANT, ColumnNames.MONTH])[ColumnNames.AMOUNT]
        .sum()
        .abs()
        .reset_index()
    )
    recurring = (
        merchant_monthly.groupby(ColumnNames.MERCHANT)
        .agg(
            months_seen=(ColumnNames.MONTH, "nunique"),
            average_amount=(ColumnNames.AMOUNT, "mean"),
            latest_amount=(ColumnNames.AMOUNT, "last"),
        )
        .reset_index()
    )
    recurring = recurring[recurring["months_seen"] >= 2].sort_values(
        ["months_seen", "average_amount"],
        ascending=[False, False],
    )
    return [
        {
            "merchant": str(row[ColumnNames.MERCHANT]),
            "months_seen": int(row["months_seen"]),
            "average_amount": float(row["average_amount"]),
            "latest_amount": float(row["latest_amount"]),
        }
        for _, row in recurring.head(limit).iterrows()
    ]


def get_duplicate_transactions(df: pd.DataFrame, limit: int = 5) -> list[DuplicateTransaction]:
    """Identify likely duplicate transactions by exact same date/account/merchant/amount."""
    if df.empty:
        return []

    grouped = (
        df.groupby([ColumnNames.DATE, ColumnNames.ACCOUNT, ColumnNames.MERCHANT, ColumnNames.AMOUNT])
        .size()
        .reset_index(name="duplicates")
    )
    grouped = grouped[grouped["duplicates"] > 1].sort_values("duplicates", ascending=False)
    return [
        {
            "merchant": str(row[ColumnNames.MERCHANT]),
            "date": pd.to_datetime(row[ColumnNames.DATE]).strftime("%b %d, %Y"),
            "account": str(row[ColumnNames.ACCOUNT]),
            "amount": float(abs(row[ColumnNames.AMOUNT])),
            "duplicates": int(row["duplicates"]),
        }
        for _, row in grouped.head(limit).iterrows()
    ]


def get_spend_recommendations(df: pd.DataFrame) -> list[str]:
    """Generate concise product-style recommendations from current spend behavior."""
    category_spending = calculate_category_spending(df)
    if category_spending.empty:
        return []

    total_spend = float(category_spending.sum())
    recommendations: list[str] = []

    top_category = str(category_spending.idxmax())
    top_amount = float(category_spending.max())
    top_share = (top_amount / total_spend * 100) if total_spend else 0.0
    recommendations.append(f"{top_category} accounts for {top_share:.1f}% of spend. Review it first.")

    recurring_merchants = get_recurring_merchants(df, limit=1)
    if recurring_merchants:
        merchant = recurring_merchants[0]
        recommendations.append(
            f"{merchant['merchant']} appears in {merchant['months_seen']} months. Confirm whether it is recurring."
        )

    anomaly = get_spend_anomaly(df)
    if anomaly:
        recommendations.append(
            f"{anomaly['date']} was {anomaly['multiple']:.1f}x a typical spend day."
        )

    return recommendations[:3]


def _pct_change(delta: float, baseline: float) -> float:
    """Calculate a safe percentage change."""
    if baseline == 0:
        return 0.0
    return delta / baseline * 100
