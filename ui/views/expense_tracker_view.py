"""Main expense tracker view coordinator.

This module manages the expense tracker interface and coordinates between different tab views.
Transactions are stored with signed amounts.
Income is identified by category == 'Income', while positive non-income rows are treated as refunds/credits.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Optional

from app_constants import ColumnNames
from data.calculations import (
    is_expense_transaction,
    is_income_transaction,
    is_refund_transaction,
)
from data.validators import validate_dataframe, validate_budget_config, validate_positive_integer
from ui.components.utils import render_tabs_safely, render_empty_state
from ui.components.surfaces import inject_surface_styles, render_accent_pills, render_section_intro
from ui.views.expense_tracker.overview import render_overview_tab
from ui.views.expense_tracker.transactions import render_transactions_tab
from ui.views.expense_tracker.budget import render_budgets_tab
from ui.views.expense_tracker.insights import render_insights_tab
from ui.views.expense_tracker.sankey import render_sankey_tab


# Tab configuration
TAB_CONFIG = [
    {'name': 'Overview', 'render_func': render_overview_tab, 'context': 'overview'},
    {'name': 'Budgets', 'render_func': render_budgets_tab, 'context': 'budgets'},
    {'name': 'Insights', 'render_func': render_insights_tab, 'context': 'insights'},
    {'name': 'Transactions', 'render_func': render_transactions_tab, 'context': 'transactions'},
    {'name': 'Sankey Chart', 'render_func': render_sankey_tab, 'context': 'sankey flow diagram'}
]


def show_expense_tracker(
    df_filtered: Optional[pd.DataFrame],
    budgets: Dict[str, float],
    num_months: int = 1,
    period_start: Optional[pd.Timestamp] = None,
    period_end: Optional[pd.Timestamp] = None,
) -> None:
    """
    Display the expense tracker interface with multiple tabs.
    
    This function orchestrates the rendering of all expense tracking views,
    including overview, transactions, budgets, insights, and cash flow analysis.
    
    Args:
        df_filtered: Filtered transactions dataframe. Must contain transaction data
                    with amount, category, and date columns.
        budgets: Dictionary of monthly budgets by category. Keys are category names,
                values are budget amounts.
        num_months: Number of distinct months in the selected date range. Used for
                   budget period calculations. Defaults to 1.
        period_start: Start of the selected expense period.
        period_end: End of the selected expense period.
        
    Returns:
        None
    """
    # Validate inputs
    required_columns = [
        ColumnNames.DATE,
        ColumnNames.AMOUNT,
        ColumnNames.CATEGORY,
        ColumnNames.MERCHANT,
        ColumnNames.ACCOUNT
    ]
    
    if not validate_dataframe(df_filtered, required_columns, context="transaction data"):
        render_empty_state(
            title="No Transaction Data",
            message="No transaction data available for the selected period.",
            show_tips=True,
            tips=[
                "Check your date range filter",
                "Ensure transaction data has been loaded",
                "Verify your data file contains the required columns"
            ]
        )
        return
    
    if not validate_budget_config(budgets):
        st.error("Invalid budget configuration. Please check your budget data.")
        return
    
    if not validate_positive_integer(num_months, "number of months"):
        return

    inject_surface_styles()
    _render_expense_tracker_summary(df_filtered, num_months, period_start, period_end)
    
    st.divider()
    
    tab_configs = [
        {
            'render_func': render_overview_tab,
            'args': [df_filtered, budgets, num_months, period_start, period_end],
            'context': 'overview',
        },
        {
            'render_func': render_budgets_tab,
            'args': [df_filtered, budgets, num_months],
            'context': 'budgets',
        },
        {
            'render_func': render_insights_tab,
            'args': [df_filtered],
            'context': 'insights',
        },
        {
            'render_func': render_transactions_tab,
            'args': [df_filtered],
            'context': 'transactions',
        },
        {
            'render_func': render_sankey_tab,
            'args': [df_filtered, budgets, num_months],
            'context': 'sankey flow diagram',
        },
    ]

    render_tabs_safely(tab_configs, [config['name'] for config in TAB_CONFIG])


def _render_expense_tracker_summary(
    df_filtered: pd.DataFrame,
    num_months: int,
    period_start: Optional[pd.Timestamp],
    period_end: Optional[pd.Timestamp],
) -> None:
    """Render a compact top-level summary so the Expense area feels cohesive."""
    if df_filtered.empty:
        return

    expense_df = df_filtered[is_expense_transaction(df_filtered)]
    income_df = df_filtered[is_income_transaction(df_filtered)]
    refund_df = df_filtered[is_refund_transaction(df_filtered)]

    if period_start is None:
        period_start = pd.to_datetime(df_filtered[ColumnNames.DATE].min())
    if period_end is None:
        period_end = pd.to_datetime(df_filtered[ColumnNames.DATE].max())

    period_days = (pd.to_datetime(period_end).normalize() - pd.to_datetime(period_start).normalize()).days + 1
    active_categories = expense_df[ColumnNames.CATEGORY].nunique() if not expense_df.empty else 0

    render_section_intro(
        "Expense Tracker",
        "Move from top-line cash flow into budgets, patterns, raw rows, and Sankey exploration without losing period context.",
    )
    render_accent_pills(
        [
            ("Period", f"{pd.to_datetime(period_start).strftime('%b %d')} - {pd.to_datetime(period_end).strftime('%b %d, %Y')}"),
            ("Window", f"{period_days} days"),
            ("Months", str(num_months)),
            ("Transactions", f"{len(df_filtered):,}"),
            ("Expense Rows", f"{len(expense_df):,}"),
            ("Refunds", f"{len(refund_df):,}"),
            ("Income", f"${income_df[ColumnNames.AMOUNT].sum():,.0f}"),
            ("Categories", str(active_categories)),
        ]
    )
