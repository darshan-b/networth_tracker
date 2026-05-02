"""Dynamic payout summary for the net worth tracker."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_constants import ColumnNames
from data.loader import load_payout_sheet_defaults
from ui.charts import (
    create_payout_mix_chart,
    create_payout_rnor_advantage_chart,
    create_payout_rnor_projection_chart,
    create_payout_tax_drag_chart,
    create_payout_total_outcome_chart,
)
from ui.components.surfaces import (
    render_accent_pills,
    render_metric_card,
    render_panel_head,
    render_section_intro,
)

LIQUIDATION_CATEGORIES = ["Credit Card", "Checkings", "Savings", "Bullion", "On Hand"]
DEFAULT_VACATION_AFTER_TAX_FACTOR = 0.73
DEFAULT_USD_TO_INR_RATE = 93.95
DEFAULT_CAPITAL_GAINS_TAX_RATE = 0.15
DEFAULT_STATE_TAX_RATE = 0.05
DEFAULT_RETIREMENT_PENALTY_RATE = 0.10
DEFAULT_HSA_ORDINARY_TAX_RATE = 0.24
DEFAULT_HSA_PENALTY_RATE = 0.20
DEFAULT_INVESTMENT_RETURN_RATE = 0.12
DEFAULT_MONTHLY_CONTRIBUTION_INR = 0.0
PROJECTION_YEARS = 15

FEDERAL_TAX_CONFIG_2025 = {
    "Single": {
        "standard_deduction": 15750.0,
        "brackets": [
            (11925.0, 0.10),
            (48475.0, 0.12),
            (103350.0, 0.22),
            (197300.0, 0.24),
            (250525.0, 0.32),
            (626350.0, 0.35),
            (float("inf"), 0.37),
        ],
    },
    "Married Filing Jointly": {
        "standard_deduction": 31500.0,
        "brackets": [
            (23850.0, 0.10),
            (96950.0, 0.12),
            (206700.0, 0.22),
            (394600.0, 0.24),
            (501050.0, 0.32),
            (751600.0, 0.35),
            (float("inf"), 0.37),
        ],
    },
    "Married Filing Separately": {
        "standard_deduction": 15750.0,
        "brackets": [
            (11925.0, 0.10),
            (48475.0, 0.12),
            (103350.0, 0.22),
            (197300.0, 0.24),
            (250525.0, 0.32),
            (375800.0, 0.35),
            (float("inf"), 0.37),
        ],
    },
    "Head of Household": {
        "standard_deduction": 23625.0,
        "brackets": [
            (17000.0, 0.10),
            (64850.0, 0.12),
            (103350.0, 0.22),
            (197300.0, 0.24),
            (250500.0, 0.32),
            (626350.0, 0.35),
            (float("inf"), 0.37),
        ],
    },
}


def _format_currency(value: float) -> str:
    return f"${value:,.0f}"


def _format_currency_detailed(value: float) -> str:
    return f"${value:,.2f}"


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_inr(value: float) -> str:
    rounded = int(round(value))
    sign = "-" if rounded < 0 else ""
    digits = str(abs(rounded))
    if len(digits) <= 3:
        return f"{sign}₹{digits}"

    last_three = digits[-3:]
    remaining = digits[:-3]
    groups: list[str] = []
    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        groups.insert(0, remaining)
    grouped = ",".join(groups + [last_three])
    return f"{sign}₹{grouped}"


def _format_inr_crore(value: float) -> str:
    crore_value = value / 10_000_000
    return f"₹{crore_value:,.2f} Cr"


def _format_crore_value(value: float) -> str:
    return f"{value / 10_000_000:,.2f}"


def _clamp_rate(rate: float) -> float:
    return min(max(rate, 0.0), 1.0)


def _build_taxable_account_label(row: pd.Series) -> str:
    institution = str(row.get(ColumnNames.INSTITUTION, "")).strip()
    account_name = str(row.get(ColumnNames.ACCOUNT, "")).strip()
    account_display = str(row.get(ColumnNames.ACCOUNT_DISPLAY, "")).strip().lower()
    account_id = str(row.get(ColumnNames.ACCOUNT_ID, "")).strip().lower()

    if institution.lower() == "fidelity":
        if "roth" in account_name.lower() or "roth" in account_display or "roth" in account_id:
            return "Fidelity Roth"
        return "Fidelity Brokerage"

    return institution or account_name or "Unknown Taxable Account"


def _compute_progressive_tax(taxable_income: float, brackets: list[tuple[float, float]]) -> float:
    if taxable_income <= 0:
        return 0.0

    total_tax = 0.0
    lower_bound = 0.0
    remaining_income = taxable_income
    for upper_bound, rate in brackets:
        bracket_width = upper_bound - lower_bound
        taxed_here = min(remaining_income, bracket_width)
        if taxed_here <= 0:
            break
        total_tax += taxed_here * rate
        remaining_income -= taxed_here
        lower_bound = upper_bound
    return total_tax


def _compute_incremental_federal_tax(
    wage_income: float,
    withdrawal_income: float,
    filing_status: str,
) -> tuple[float, float, float]:
    config = FEDERAL_TAX_CONFIG_2025[filing_status]
    standard_deduction = config["standard_deduction"]
    brackets = config["brackets"]
    base_taxable_income = max(wage_income - standard_deduction, 0.0)
    total_taxable_income = max(wage_income + withdrawal_income - standard_deduction, 0.0)
    base_federal_tax = _compute_progressive_tax(base_taxable_income, brackets)
    total_federal_tax = _compute_progressive_tax(total_taxable_income, brackets)
    incremental_federal_tax = max(total_federal_tax - base_federal_tax, 0.0)
    return incremental_federal_tax, base_taxable_income, total_taxable_income


def _build_federal_bracket_breakdown(
    wage_income: float,
    withdrawal_income: float,
    filing_status: str,
) -> pd.DataFrame:
    config = FEDERAL_TAX_CONFIG_2025[filing_status]
    standard_deduction = config["standard_deduction"]
    brackets = config["brackets"]
    base_taxable_income = max(wage_income - standard_deduction, 0.0)
    total_taxable_income = max(wage_income + withdrawal_income - standard_deduction, 0.0)

    rows = []
    lower_bound = 0.0
    for upper_bound, rate in brackets:
        bracket_top = upper_bound if upper_bound != float("inf") else total_taxable_income
        if bracket_top <= lower_bound:
            lower_bound = upper_bound
            continue

        wage_used = max(min(base_taxable_income, upper_bound) - lower_bound, 0.0)
        total_used = max(min(total_taxable_income, upper_bound) - lower_bound, 0.0)
        withdrawal_used = max(total_used - wage_used, 0.0)
        bracket_tax = withdrawal_used * rate

        if wage_used > 0 or withdrawal_used > 0:
            if upper_bound == float("inf"):
                bracket_range = f"${lower_bound:,.0f}+"
            else:
                bracket_range = f"${lower_bound:,.0f} - ${upper_bound:,.0f}"
            rows.append(
                {
                    "Bracket Range": bracket_range,
                    "Rate": _format_percent(rate),
                    "Wage Income In Bracket": wage_used,
                    "Withdrawal In Bracket": withdrawal_used,
                    "Federal Tax From Withdrawal": bracket_tax,
                }
            )

        lower_bound = upper_bound

    return pd.DataFrame(rows)


def _build_retirement_tax_breakdown(
    wage_income: float,
    withdrawal_income: float,
    filing_status: str,
    state_tax_rate: float,
    retirement_penalty_rate: float,
    india_overlay_rate: float = 0.0,
) -> pd.DataFrame:
    federal_df = _build_federal_bracket_breakdown(
        wage_income=wage_income,
        withdrawal_income=withdrawal_income,
        filing_status=filing_status,
    )

    rows: list[dict[str, object]] = []
    if not federal_df.empty:
        for _, row in federal_df.iterrows():
            withdrawal_in_bracket = float(row["Withdrawal In Bracket"])
            federal_tax = float(row["Federal Tax From Withdrawal"])
            if withdrawal_in_bracket <= 0:
                continue
            rows.append(
                {
                    "Layer": f"Federal {row['Rate']} bracket",
                    "Tax Base": withdrawal_in_bracket,
                    "Rate": row["Rate"],
                    "Tax": federal_tax,
                }
            )

    rows.append(
        {
            "Layer": "State tax",
            "Tax Base": withdrawal_income,
            "Rate": _format_percent(state_tax_rate),
            "Tax": withdrawal_income * state_tax_rate,
        }
    )
    rows.append(
        {
            "Layer": "Early withdrawal penalty",
            "Tax Base": withdrawal_income,
            "Rate": _format_percent(retirement_penalty_rate),
            "Tax": withdrawal_income * retirement_penalty_rate,
        }
    )
    rows.append(
        {
            "Layer": "India overlay",
            "Tax Base": withdrawal_income,
            "Rate": _format_percent(india_overlay_rate),
            "Tax": withdrawal_income * india_overlay_rate,
        }
    )
    rows.append(
        {
            "Layer": "Total retirement tax drag",
            "Tax Base": withdrawal_income,
            "Rate": _format_percent((sum(float(item["Tax"]) for item in rows) / withdrawal_income) if withdrawal_income > 0 else 0.0),
            "Tax": sum(float(item["Tax"]) for item in rows),
        }
    )
    return pd.DataFrame(rows)


def _build_retirement_scenario(
    label: str,
    wage_income: float,
    filing_status: str,
    retirement_balance: float,
    state_tax_rate: float,
    retirement_penalty_rate: float,
    india_overlay_rate: float = 0.0,
    note: str = "",
) -> dict[str, object]:
    federal_tax, base_taxable_income, total_taxable_income = _compute_incremental_federal_tax(
        wage_income=wage_income,
        withdrawal_income=retirement_balance,
        filing_status=filing_status,
    )
    state_tax = retirement_balance * state_tax_rate
    penalty_tax = retirement_balance * retirement_penalty_rate
    india_overlay_tax = retirement_balance * india_overlay_rate
    total_tax = federal_tax + state_tax + penalty_tax + india_overlay_tax
    net_payout = retirement_balance - total_tax
    effective_rate = (total_tax / retirement_balance) if retirement_balance > 0 else 0.0
    return {
        "label": label,
        "note": note,
        "wage_income": wage_income,
        "base_taxable_income": base_taxable_income,
        "total_taxable_income": total_taxable_income,
        "federal_tax": federal_tax,
        "state_tax": state_tax,
        "penalty_tax": penalty_tax,
        "india_overlay_tax": india_overlay_tax,
        "total_tax": total_tax,
        "net_payout": net_payout,
        "effective_rate": effective_rate,
    }


def _build_total_scenario(
    label: str,
    note: str,
    liquidation_total: float,
    taxable_balance: float,
    taxable_gain_assumption: float,
    taxable_gain_tax_rate: float,
    hsa_payout: float,
    vacation_payout: float,
    retirement_scenario: dict[str, object],
    usd_to_inr_rate: float,
) -> dict[str, object]:
    taxable_tax = taxable_gain_assumption * taxable_gain_tax_rate
    taxable_net = taxable_balance - taxable_tax
    total_usd = liquidation_total + taxable_net + hsa_payout + vacation_payout + float(retirement_scenario["net_payout"])
    return {
        "label": label,
        "note": note,
        "liquidation_total": liquidation_total,
        "taxable_tax": taxable_tax,
        "taxable_net": taxable_net,
        "retirement_net": float(retirement_scenario["net_payout"]),
        "retirement_federal_tax": float(retirement_scenario["federal_tax"]),
        "retirement_state_tax": float(retirement_scenario["state_tax"]),
        "retirement_penalty_tax": float(retirement_scenario["penalty_tax"]),
        "retirement_india_overlay_tax": float(retirement_scenario["india_overlay_tax"]),
        "total_usd": total_usd,
        "total_inr": total_usd * usd_to_inr_rate,
        "effective_retirement_rate": float(retirement_scenario["effective_rate"]),
        "wage_income": float(retirement_scenario["wage_income"]),
    }


def _build_rnor_projection_dataframe(
    rnor_total_inr: float,
    annual_return_rate: float,
    monthly_contribution_inr: float,
    projection_years: int = PROJECTION_YEARS,
) -> pd.DataFrame:
    invested_principal = max(rnor_total_inr, 0.0)
    monthly_return_rate = annual_return_rate / 12
    monthly_contribution = max(monthly_contribution_inr, 0.0)

    rows: list[dict[str, float | int]] = []
    for year in range(projection_years + 1):
        total_value = invested_principal
        months_elapsed = year * 12
        if months_elapsed > 0:
            for _ in range(months_elapsed):
                total_value = (total_value + monthly_contribution) * (1 + monthly_return_rate)
        contribution_value = monthly_contribution * months_elapsed
        return_value = total_value - invested_principal - contribution_value
        rows.append(
            {
                "Year": year,
                "Principal INR": invested_principal,
                "Contributions INR": contribution_value,
                "Return INR": return_value,
                "Total INR": total_value,
                "Principal Crores": invested_principal / 10_000_000,
                "Contributions Crores": contribution_value / 10_000_000,
                "Return Crores": return_value / 10_000_000,
                "Total Crores": total_value / 10_000_000,
                "Monthly Return Rate": monthly_return_rate,
            }
        )
    return pd.DataFrame(rows)


def _is_hsa_account(row: pd.Series) -> bool:
    institution = str(row.get(ColumnNames.INSTITUTION, "")).strip().lower()
    account_id = str(row.get(ColumnNames.ACCOUNT_ID, "")).strip().lower()
    category = str(row.get(ColumnNames.CATEGORY, "")).strip().lower()
    return "hsa" in institution or "hsa" in account_id or category == "hsa"


def _build_taxable_payout_rows(
    latest_df: pd.DataFrame,
    capital_gains_tax_rate: float,
    state_tax_rate: float,
    profit_assumptions: dict[str, float],
) -> pd.DataFrame:
    working_source = latest_df.copy()
    for column in [ColumnNames.CATEGORY, ColumnNames.INSTITUTION, ColumnNames.ACCOUNT_ID]:
        if column not in working_source.columns:
            working_source[column] = ""

    taxable_df = working_source[working_source[ColumnNames.CATEGORY] == "Taxable"].copy()
    if taxable_df.empty:
        return pd.DataFrame(
            columns=[
                "Account",
                "Current Balance",
                "Principal",
                "Embedded Profit",
                "Tax Rate Used",
                "Estimated Tax",
                "Estimated Payout",
            ]
        )

    effective_tax_rate = _clamp_rate(capital_gains_tax_rate + state_tax_rate)

    working_df = taxable_df.copy()
    working_df[ColumnNames.INSTITUTION] = working_df[ColumnNames.INSTITUTION].fillna("").astype(str).str.strip()
    working_df["taxable_account_label"] = working_df.apply(_build_taxable_account_label, axis=1)
    working_df["profit_assumption"] = working_df.apply(
        lambda row: profit_assumptions.get(str(row["taxable_account_label"]), 0.0),
        axis=1,
    )
    working_df["principal"] = working_df[ColumnNames.AMOUNT] - working_df["profit_assumption"]
    working_df["estimated_tax"] = working_df["profit_assumption"] * effective_tax_rate
    working_df["estimated_payout"] = working_df[ColumnNames.AMOUNT] - working_df["estimated_tax"]
    working_df["tax_rate_used"] = effective_tax_rate
    working_df["Account"] = working_df["taxable_account_label"]

    display_df = working_df[
        [
            "Account",
            ColumnNames.AMOUNT,
            "principal",
            "profit_assumption",
            "tax_rate_used",
            "estimated_tax",
            "estimated_payout",
        ]
    ].rename(
        columns={
            ColumnNames.AMOUNT: "Current Balance",
            "principal": "Principal",
            "profit_assumption": "Embedded Profit",
            "tax_rate_used": "Tax Rate Used",
            "estimated_tax": "Estimated Tax",
            "estimated_payout": "Estimated Payout",
        }
    )
    return display_df.sort_values("Estimated Payout", ascending=False).reset_index(drop=True)


def _build_payout_payload(df_filtered: pd.DataFrame, rate_config: dict[str, object]) -> dict[str, object]:
    latest_month = df_filtered[ColumnNames.MONTH].max()
    latest_df = df_filtered[df_filtered[ColumnNames.MONTH] == latest_month].copy()
    latest_label = latest_df[ColumnNames.MONTH_STR].iloc[0]

    for column in [ColumnNames.CATEGORY, ColumnNames.INSTITUTION, ColumnNames.ACCOUNT_ID]:
        if column not in latest_df.columns:
            latest_df[column] = ""

    liquidation_df = latest_df[latest_df[ColumnNames.CATEGORY].isin(LIQUIDATION_CATEGORIES)].copy()
    taxable_rows = _build_taxable_payout_rows(
        latest_df,
        capital_gains_tax_rate=rate_config["capital_gains_tax_rate"],
        state_tax_rate=rate_config["state_tax_rate"],
        profit_assumptions=rate_config["taxable_profit_assumptions"],
    )
    taxable_payout = float(taxable_rows["Estimated Payout"].sum()) if not taxable_rows.empty else 0.0
    taxable_balance = float(taxable_rows["Current Balance"].sum()) if not taxable_rows.empty else 0.0

    tax_advantaged_df = latest_df[latest_df[ColumnNames.CATEGORY] == "Tax-Advantaged"].copy()
    hsa_df = tax_advantaged_df[tax_advantaged_df.apply(_is_hsa_account, axis=1)].copy()
    retirement_df = tax_advantaged_df[~tax_advantaged_df.apply(_is_hsa_account, axis=1)].copy()

    retirement_balance = float(retirement_df[ColumnNames.AMOUNT].sum()) if not retirement_df.empty else 0.0
    retirement_federal_tax, base_taxable_income, total_taxable_income = _compute_incremental_federal_tax(
        wage_income=float(rate_config["wage_income"]),
        withdrawal_income=retirement_balance,
        filing_status=str(rate_config["filing_status"]),
    )
    retirement_state_tax = retirement_balance * float(rate_config["state_tax_rate"])
    retirement_penalty = retirement_balance * float(rate_config["retirement_penalty_rate"])
    retirement_total_tax = retirement_federal_tax + retirement_state_tax + retirement_penalty
    retirement_effective_rate = (retirement_total_tax / retirement_balance) if retirement_balance > 0 else 0.0
    retirement_payout = retirement_balance - retirement_total_tax

    hsa_balance = float(hsa_df[ColumnNames.AMOUNT].sum()) if not hsa_df.empty else 0.0
    qualified_hsa_amount = min(hsa_balance, rate_config["qualified_hsa_expense_amount"])
    taxable_hsa_amount = max(hsa_balance - qualified_hsa_amount, 0.0)
    hsa_effective_rate = _clamp_rate(rate_config["hsa_ordinary_tax_rate"] + rate_config["hsa_penalty_rate"])
    hsa_payout = qualified_hsa_amount + taxable_hsa_amount * (1 - hsa_effective_rate)

    vacation_hourly_rate = float(rate_config["annual_salary"]) / (52 * 40)
    vacation_payout = vacation_hourly_rate * float(rate_config["vacation_hours"]) * rate_config["vacation_after_tax_factor"]

    liquidation_total = float(liquidation_df[ColumnNames.AMOUNT].sum())
    total_usd = liquidation_total + taxable_payout + retirement_payout + hsa_payout + vacation_payout

    component_df = pd.DataFrame(
        [
            {
                "Component": "Cash / savings / bullion / on-hand / credit cards",
                "Workbook Logic": "100% of selected categories",
                "Current Value": liquidation_total,
                "Payout Value": liquidation_total,
            },
            {
                "Component": "Taxable accounts",
                "Workbook Logic": (
                    "Current balance - embedded gain tax "
                    f"({_format_percent(_clamp_rate(rate_config['capital_gains_tax_rate'] + rate_config['state_tax_rate']))})"
                ),
                "Current Value": taxable_balance,
                "Payout Value": taxable_payout,
            },
            {
                "Component": "Traditional retirement accounts",
                "Workbook Logic": (
                    "Current balance - progressive federal tax - state tax - early penalty "
                    f"({_format_percent(retirement_effective_rate)} total)"
                ),
                "Current Value": retirement_balance,
                "Payout Value": retirement_payout,
            },
            {
                "Component": "HSA",
                "Workbook Logic": (
                    f"Qualified medical amount at 0%, remainder at {_format_percent(hsa_effective_rate)}"
                ),
                "Current Value": hsa_balance,
                "Payout Value": hsa_payout,
            },
            {
                "Component": "Vacation payout",
                "Workbook Logic": (
                    f"($102,000 / (52*40)) * 352 * {_format_percent(rate_config['vacation_after_tax_factor'])}"
                ),
                "Current Value": vacation_payout,
                "Payout Value": vacation_payout,
            },
        ]
    )

    return {
        "latest_label": latest_label,
        "liquidation_total": liquidation_total,
        "taxable_balance": taxable_balance,
        "taxable_gain_assumption": float(taxable_rows["Embedded Profit"].sum()) if not taxable_rows.empty else 0.0,
        "taxable_payout": taxable_payout,
        "retirement_balance": retirement_balance,
        "retirement_payout": retirement_payout,
        "retirement_effective_rate": retirement_effective_rate,
        "retirement_federal_tax": retirement_federal_tax,
        "retirement_state_tax": retirement_state_tax,
        "retirement_penalty": retirement_penalty,
        "hsa_balance": hsa_balance,
        "hsa_payout": hsa_payout,
        "hsa_effective_rate": hsa_effective_rate,
        "qualified_hsa_amount": qualified_hsa_amount,
        "vacation_payout": vacation_payout,
        "fixed_non_retirement_payout": liquidation_total + taxable_payout + hsa_payout + vacation_payout,
        "total_usd": total_usd,
        "total_inr": total_usd * rate_config["usd_to_inr_rate"],
        "taxable_rows": taxable_rows,
        "component_df": component_df,
        "retirement_tax_breakdown_df": _build_retirement_tax_breakdown(
            wage_income=float(rate_config["wage_income"]),
            withdrawal_income=retirement_balance,
            filing_status=str(rate_config["filing_status"]),
            state_tax_rate=float(rate_config["state_tax_rate"]),
            retirement_penalty_rate=float(rate_config["retirement_penalty_rate"]),
        ),
        "base_taxable_income": base_taxable_income,
        "total_taxable_income": total_taxable_income,
    }


def show_payout_view(df_filtered: pd.DataFrame) -> None:
    """Render the payout tab with explicit early-withdrawal rates."""
    if df_filtered.empty:
        st.warning("No net worth data available for payout analysis.")
        return

    workbook_defaults = load_payout_sheet_defaults()
    if not bool(workbook_defaults["available"]):
        st.error("Payout analysis requires workbook-backed payout assumptions.")
        st.caption(f"Source: `{workbook_defaults['source']}`")
        missing_fields = workbook_defaults.get("missing_fields", [])
        if missing_fields:
            st.info(f"Missing payout sheet inputs: {', '.join(str(field) for field in missing_fields)}.")
        elif workbook_defaults.get("error"):
            st.info(f"Unable to read payout sheet inputs. Details: {workbook_defaults['error']}")
        return

    render_panel_head(
        "neutral",
        "Payout",
        "Early Withdrawal Payout Model",
        "Progressive federal brackets, explicit state and penalty rates, and a two-scenario timing comparison.",
        "Worst case means withdrawing on the last day of the year after the wage bucket has already been earned.",
    )

    with st.expander("Assumptions", expanded=False):
        controls_col1, controls_col2, controls_col3 = st.columns(3)
        with controls_col1:
            filing_status = st.selectbox(
                "Federal Filing Status",
                list(FEDERAL_TAX_CONFIG_2025.keys()),
                index=0,
                key="payout_filing_status",
            )
            wage_income = st.number_input(
                "Wage Bucket For Tax Calculation",
                min_value=0.0,
                value=float(workbook_defaults["annual_salary"]),
                step=1000.0,
                format="%.2f",
                key="payout_wage_income",
            )
            usd_to_inr_rate = st.number_input(
                "USD to INR Rate",
                min_value=0.01,
                value=float(workbook_defaults["usd_to_inr_rate"]),
                step=0.01,
                format="%.2f",
                key="payout_manual_fx_rate",
            )
            capital_gains_tax_rate = st.number_input(
                "Taxable Capital Gains Tax Rate",
                min_value=0.0,
                max_value=1.0,
                value=float(workbook_defaults["capital_gains_tax_rate"]),
                step=0.01,
                format="%.2f",
                key="payout_capital_gains_tax_rate",
            )
        with controls_col2:
            state_tax_rate = st.number_input(
                "State Tax Rate",
                min_value=0.0,
                max_value=1.0,
                value=float(DEFAULT_STATE_TAX_RATE),
                step=0.01,
                format="%.2f",
                key="payout_state_tax_rate",
            )
            retirement_penalty_rate = st.number_input(
                "Traditional Retirement Early Withdrawal Penalty",
                min_value=0.0,
                max_value=1.0,
                value=float(DEFAULT_RETIREMENT_PENALTY_RATE),
                step=0.01,
                format="%.2f",
                key="payout_retirement_penalty_rate",
            )
            vacation_after_tax_factor = st.number_input(
                "Vacation After-Tax Factor",
                min_value=0.0,
                max_value=1.0,
                value=float(workbook_defaults["vacation_after_tax_factor"]),
                step=0.01,
                format="%.2f",
                key="payout_vacation_after_tax_factor",
            )
        with controls_col3:
            hsa_ordinary_tax_rate = st.number_input(
                "HSA Non-Qualified Income Tax Rate",
                min_value=0.0,
                max_value=1.0,
                value=float(DEFAULT_HSA_ORDINARY_TAX_RATE),
                step=0.01,
                format="%.2f",
                key="payout_hsa_ordinary_tax_rate",
            )
            hsa_penalty_rate = st.number_input(
                "HSA Non-Qualified Penalty",
                min_value=0.0,
                max_value=1.0,
                value=float(DEFAULT_HSA_PENALTY_RATE),
                step=0.01,
                format="%.2f",
                key="payout_hsa_penalty_rate",
            )
            qualified_hsa_expense_amount = st.number_input(
                "Qualified HSA Expense Amount",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
                key="payout_qualified_hsa_expense_amount",
            )

    rate_config = {
        "filing_status": filing_status,
        "wage_income": float(wage_income),
        "usd_to_inr_rate": float(usd_to_inr_rate),
        "capital_gains_tax_rate": float(capital_gains_tax_rate),
        "state_tax_rate": float(state_tax_rate),
        "retirement_penalty_rate": float(retirement_penalty_rate),
        "hsa_ordinary_tax_rate": float(hsa_ordinary_tax_rate),
        "hsa_penalty_rate": float(hsa_penalty_rate),
        "qualified_hsa_expense_amount": float(qualified_hsa_expense_amount),
        "vacation_after_tax_factor": float(vacation_after_tax_factor),
        "taxable_profit_assumptions": dict(workbook_defaults["taxable_profit_assumptions"]),
        "annual_salary": float(workbook_defaults["annual_salary"]),
        "vacation_hours": float(workbook_defaults["vacation_hours"]),
    }

    payload = _build_payout_payload(df_filtered, rate_config=rate_config)

    withdraw_now_retirement = _build_retirement_scenario(
            label="Withdraw Now",
            wage_income=float(wage_income),
            filing_status=filing_status,
            retirement_balance=float(payload["retirement_balance"]),
            state_tax_rate=float(state_tax_rate),
            retirement_penalty_rate=float(retirement_penalty_rate),
            note="Full U.S. wage bucket already earned.",
        )
    new_year_rnor_retirement = _build_retirement_scenario(
            label="New Year RNOR",
            wage_income=0.0,
            filing_status=filing_status,
            retirement_balance=float(payload["retirement_balance"]),
            state_tax_rate=float(state_tax_rate),
            retirement_penalty_rate=float(retirement_penalty_rate),
            note="Assumes $0 U.S. wages and nonresident capital-gains treatment.",
        )
    scenarios = [
        _build_total_scenario(
            label="Withdraw Now",
            note="Full U.S. wage bucket already earned. Taxable gains still use the entered capital-gains rate.",
            liquidation_total=float(payload["liquidation_total"]),
            taxable_balance=float(payload["taxable_balance"]),
            taxable_gain_assumption=float(payload["taxable_gain_assumption"]),
            taxable_gain_tax_rate=_clamp_rate(float(capital_gains_tax_rate) + float(state_tax_rate)),
            hsa_payout=float(payload["hsa_payout"]),
            vacation_payout=float(payload["vacation_payout"]),
            retirement_scenario=withdraw_now_retirement,
            usd_to_inr_rate=float(usd_to_inr_rate),
        ),
        _build_total_scenario(
            label="New Year RNOR",
            note="Assumes $0 U.S. wages and nonresident capital-gains treatment, so the taxable brokerage gain tax is set to 0%.",
            liquidation_total=float(payload["liquidation_total"]),
            taxable_balance=float(payload["taxable_balance"]),
            taxable_gain_assumption=float(payload["taxable_gain_assumption"]),
            taxable_gain_tax_rate=0.0,
            hsa_payout=float(payload["hsa_payout"]),
            vacation_payout=float(payload["vacation_payout"]),
            retirement_scenario=new_year_rnor_retirement,
            usd_to_inr_rate=float(usd_to_inr_rate),
        ),
    ]
    best_scenario = max(scenarios, key=lambda item: float(item["total_usd"]))
    worst_scenario = min(scenarios, key=lambda item: float(item["total_usd"]))

    render_accent_pills(
        [
            ("Snapshot", str(payload["latest_label"])),
            ("Filing Status", filing_status),
            ("Wage Bucket", _format_currency(wage_income)),
            ("Std Deduction", _format_currency(FEDERAL_TAX_CONFIG_2025[filing_status]["standard_deduction"])),
            ("Taxable Gain Rate Now", _format_percent(capital_gains_tax_rate + state_tax_rate)),
            ("Taxable Gain Rate RNOR", "0.0%"),
            ("Retirement Penalty", _format_percent(retirement_penalty_rate)),
            ("HSA Rate", _format_percent(payload["hsa_effective_rate"])),
        ]
    )

    headline_cols = st.columns(4)
    spread_usd = float(best_scenario["total_usd"]) - float(worst_scenario["total_usd"])
    with headline_cols[0]:
        render_metric_card(
            "Best Scenario",
            str(best_scenario["label"]),
            _format_currency(float(best_scenario["total_usd"])),
            _format_inr_crore(float(best_scenario["total_inr"])),
            "positive",
        )
    with headline_cols[1]:
        render_metric_card(
            "Spread",
            _format_currency(spread_usd),
            _format_inr_crore(spread_usd * float(usd_to_inr_rate)),
            "Gap between the two modeled outcomes.",
            "neutral",
        )
    with headline_cols[2]:
        render_metric_card(
            "Retirement Bucket",
            _format_currency(float(payload["retirement_balance"])),
            _format_percent(float(payload["retirement_effective_rate"])),
            "Modeled using progressive federal tax plus state and penalty.",
            "neutral",
        )
    with headline_cols[3]:
        render_metric_card(
            "Taxable Embedded Gain",
            _format_currency(float(payload["taxable_gain_assumption"])),
            _format_currency(float(payload["taxable_balance"])),
            "Workbook-based gain assumption inside the taxable bucket.",
            "neutral",
        )

    scenario_cols = st.columns(2)
    tones = ["negative", "positive"]
    for col, scenario, tone in zip(scenario_cols, scenarios, tones):
        with col:
            render_metric_card(
                str(scenario["label"]),
                _format_currency(float(scenario["total_usd"])),
                _format_inr_crore(float(scenario["total_inr"])),
                scenario["note"],
                tone,
            )

    total_chart_col, bridge_col = st.columns([1.15, 1.0])
    with total_chart_col:
        st.plotly_chart(create_payout_total_outcome_chart(scenarios), use_container_width=True)
    with bridge_col:
        st.plotly_chart(
            create_payout_rnor_advantage_chart(scenarios[0], scenarios[1]),
            use_container_width=True,
        )

    st.divider()
    breakdown_col, tax_col = st.columns(2)
    with breakdown_col:
        st.caption("Where payout comes from")
        st.plotly_chart(
            create_payout_mix_chart(
                scenarios,
                hsa_payout=float(payload["hsa_payout"]),
                vacation_payout=float(payload["vacation_payout"]),
            ),
            use_container_width=True,
        )
    with tax_col:
        st.caption("What drags it down")
        st.plotly_chart(create_payout_tax_drag_chart(scenarios), use_container_width=True)

    summary_cols = st.columns(3)
    savings_delta = float(scenarios[1]["total_usd"]) - float(scenarios[0]["total_usd"])
    retirement_tax_delta = (
        float(scenarios[0]["retirement_federal_tax"])
        + float(scenarios[0]["retirement_state_tax"])
        + float(scenarios[0]["retirement_penalty_tax"])
    ) - (
        float(scenarios[1]["retirement_federal_tax"])
        + float(scenarios[1]["retirement_state_tax"])
        + float(scenarios[1]["retirement_penalty_tax"])
    )
    taxable_tax_delta = float(scenarios[0]["taxable_tax"]) - float(scenarios[1]["taxable_tax"])

    with summary_cols[0]:
        render_metric_card(
            "RNOR Delta",
            _format_currency(savings_delta),
            _format_inr_crore(savings_delta * float(usd_to_inr_rate)),
            "Incremental cash from waiting for the new year under the RNOR assumption.",
            "positive" if savings_delta >= 0 else "negative",
        )
    with summary_cols[1]:
        render_metric_card(
            "Retirement Tax Saved",
            _format_currency(retirement_tax_delta),
            _format_percent(
                (retirement_tax_delta / float(payload["retirement_balance"]))
                if float(payload["retirement_balance"]) > 0
                else 0.0
            ),
            "Federal, state, and penalty savings on the retirement bucket.",
            "neutral",
        )
    with summary_cols[2]:
        render_metric_card(
            "Taxable Gain Tax Saved",
            _format_currency(taxable_tax_delta),
            _format_percent(
                (taxable_tax_delta / float(payload["taxable_gain_assumption"]))
                if float(payload["taxable_gain_assumption"]) > 0
                else 0.0
            ),
            "Savings from applying the RNOR capital-gains assumption to the taxable bucket.",
            "neutral",
        )

    st.divider()
    render_section_intro(
        "RNOR Deployment",
        f"Under the RNOR path, invest the full payout and project it forward over {PROJECTION_YEARS} years.",
    )
    rnor_control_col1, rnor_control_col2, rnor_control_col3 = st.columns(3)
    with rnor_control_col1:
        annual_return_rate = st.number_input(
            "RNOR Annual Interest Rate",
            min_value=0.0,
            max_value=1.0,
            value=float(DEFAULT_INVESTMENT_RETURN_RATE),
            step=0.01,
            format="%.2f",
            key="payout_annual_return_rate",
        )
    with rnor_control_col2:
        monthly_contribution_inr = st.number_input(
            "RNOR Monthly Contribution (INR)",
            min_value=0.0,
            value=float(DEFAULT_MONTHLY_CONTRIBUTION_INR),
            step=10000.0,
            format="%.0f",
            key="payout_monthly_contribution_inr",
        )
    with rnor_control_col3:
        st.caption("Compounding")
        st.caption("Monthly")

    rnor_scenario = next(scenario for scenario in scenarios if str(scenario["label"]) == "New Year RNOR")
    rnor_projection_df = _build_rnor_projection_dataframe(
        rnor_total_inr=float(rnor_scenario["total_inr"]),
        annual_return_rate=float(annual_return_rate),
        monthly_contribution_inr=float(monthly_contribution_inr),
        projection_years=PROJECTION_YEARS,
    )
    initial_projection = rnor_projection_df.iloc[0]
    final_projection = rnor_projection_df.iloc[-1]
    projection_gain_inr = float(final_projection["Total INR"]) - float(initial_projection["Total INR"])

    deployment_cols = st.columns(3)
    with deployment_cols[0]:
        render_metric_card(
            "RNOR Starting Principal",
            _format_inr_crore(float(initial_projection["Principal INR"])),
            _format_currency(float(initial_projection["Principal INR"]) / float(usd_to_inr_rate)),
            "Entire RNOR payout assumed invested at year 0.",
            "positive",
        )
    with deployment_cols[1]:
        render_metric_card(
            "Contribution Added",
            _format_inr_crore(float(final_projection["Contributions INR"])),
            _format_inr(monthly_contribution_inr),
            "Total monthly contributions added across the projection window.",
            "neutral",
        )
    with deployment_cols[2]:
        render_metric_card(
            f"Year {PROJECTION_YEARS} Return",
            _format_inr_crore(float(final_projection["Return INR"])),
            _format_percent(
                (
                    float(final_projection["Return INR"])
                    / (
                        float(initial_projection["Principal INR"])
                        + float(final_projection["Contributions INR"])
                    )
                )
                if (float(initial_projection["Principal INR"]) + float(final_projection["Contributions INR"])) > 0
                else 0.0
            ),
            "Accumulated gain above the original principal.",
            "positive",
        )

    value_cols = st.columns(2)
    with value_cols[0]:
        render_metric_card(
            f"Year {PROJECTION_YEARS} Value",
            _format_inr_crore(float(final_projection["Total INR"])),
            _format_inr_crore(projection_gain_inr),
            "Projected total after compounding principal, contributions, and returns.",
            "positive",
        )
    with value_cols[1]:
        render_metric_card(
            "Year 15 Total Added Capital",
            _format_inr_crore(float(initial_projection["Principal INR"]) + float(final_projection["Contributions INR"])),
            _format_inr_crore(float(final_projection["Return INR"])),
            "Capital invested versus wealth created by return.",
            "neutral",
        )

    st.plotly_chart(create_payout_rnor_projection_chart(rnor_projection_df), use_container_width=True)

    with st.expander("See Tax Layers", expanded=False):
        for scenario in scenarios:
            st.markdown(f"**{scenario['label']}**")
            scenario_breakdown_df = _build_retirement_tax_breakdown(
                wage_income=float(scenario["wage_income"]),
                withdrawal_income=float(payload["retirement_balance"]),
                filing_status=filing_status,
                state_tax_rate=float(state_tax_rate),
                retirement_penalty_rate=float(retirement_penalty_rate),
                india_overlay_rate=float(scenario["retirement_india_overlay_tax"]) / float(payload["retirement_balance"]) if float(payload["retirement_balance"]) > 0 else 0.0,
            )
            for column in ["Tax Base", "Tax"]:
                scenario_breakdown_df[column] = scenario_breakdown_df[column].map(_format_currency_detailed)
            st.dataframe(scenario_breakdown_df, width="stretch", hide_index=True)

    with st.expander("Model Notes", expanded=False):
        st.caption(
            "This early-withdrawal model is more explicit than the old 65% and 85% shortcuts, "
            "but it still uses embedded gain assumptions from the workbook because the dataset does not contain full tax basis history."
        )
