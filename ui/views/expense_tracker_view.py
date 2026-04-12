"""Main expense tracker view coordinator.

This module manages the expense tracker interface and coordinates between different tab views.
Transactions are stored with negative amounts for expenses and positive for income.
Income is identified by category == 'Income'.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Optional

from app_constants import ColumnNames
from data.filters import filter_expenses
from data.validators import validate_dataframe, validate_budget_config, validate_positive_integer
from ui.components.utils import render_tabs_safely, render_empty_state
from ui.views.expense_tracker.overview import render_overview_tab
from ui.views.expense_tracker.transactions import render_transactions_tab
from ui.views.expense_tracker.budget import render_budgets_tab
from ui.views.expense_tracker.insights import render_insights_tab
from ui.views.expense_tracker.sankey import render_sankey_tab


# Tab configuration
TAB_CONFIG = [
    {'name': 'Overview', 'render_func': render_overview_tab, 'context': 'overview'},
    {'name': 'Transactions', 'render_func': render_transactions_tab, 'context': 'transactions'},
    {'name': 'Budgets', 'render_func': render_budgets_tab, 'context': 'budgets'},
    {'name': 'Insights', 'render_func': render_insights_tab, 'context': 'insights'},
    {'name': 'Sankey Chart', 'render_func': render_sankey_tab, 'context': 'sankey flow diagram'}
]


def show_expense_tracker(
    df_filtered: Optional[pd.DataFrame],
    budgets: Dict[str, float],
    num_months: int = 1
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
    
    st.divider()
    
    # Filter for expenses (for tabs that only need expense data)
    df_expenses = filter_expenses(df_filtered)

    tab_configs = [
        {
            'render_func': render_overview_tab,
            'args': [df_filtered, budgets, num_months],
            'context': 'overview',
        },
        {
            'render_func': render_transactions_tab,
            'args': [df_filtered],
            'context': 'transactions',
        },
        {
            'render_func': render_budgets_tab,
            'args': [df_expenses, budgets, num_months],
            'context': 'budgets',
        },
        {
            'render_func': render_insights_tab,
            'args': [df_filtered],
            'context': 'insights',
        },
        {
            'render_func': render_sankey_tab,
            'args': [df_filtered, budgets, num_months],
            'context': 'sankey flow diagram',
        },
    ]

    render_tabs_safely(tab_configs, [config['name'] for config in TAB_CONFIG])
