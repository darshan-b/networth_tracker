"""Main expense tracker view coordinator.

This module manages the expense tracker interface and coordinates between different tab views.
Transactions are stored with negative amounts for expenses and positive for income.
Income is identified by category == 'Income'.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Optional

from data.filters import filter_expenses
from ui.views.expense_tracker.overview import render_overview_tab
from ui.views.expense_tracker.transactions import render_transactions_tab
from ui.views.expense_tracker.budget import render_budgets_tab
from ui.views.expense_tracker.insights import render_insights_tab
from ui.views.expense_tracker.sankey import render_sankey_tab


# Tab name constants
TAB_OVERVIEW = "Overview"
TAB_TRANSACTIONS = "Transactions"
TAB_BUDGETS = "Budgets"
TAB_INSIGHTS = "Insights"
TAB_SANKEY = "Cash Flow"


def show_expense_tracker(df_filtered: Optional[pd.DataFrame], budgets: Dict[str, float], num_months: int = 1) -> None:
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
        
    Raises:
        Does not raise exceptions directly, but displays error messages to the UI
        when invalid inputs are detected or rendering errors occur.
    """
    # Validate inputs
    if df_filtered is None or df_filtered.empty:
        st.warning("No transaction data available for the selected period.")
        return
    
    if not isinstance(budgets, dict):
        st.error("Invalid budget configuration. Please check your budget data.")
        return
    
    if num_months < 1:
        st.error(f"Invalid number of months: {num_months}. Must be at least 1.")
        return
    
    st.divider()
    
    # Create navigation tabs
    tabs = st.tabs([
        TAB_OVERVIEW,
        TAB_TRANSACTIONS,
        TAB_BUDGETS,
        TAB_INSIGHTS,
        TAB_SANKEY
    ])
    
    # Filter for expenses (for tabs that only need expense data)
    df_expenses = filter_expenses(df_filtered)
    
    # Render Overview tab
    with tabs[0]:
        try:
            render_overview_tab(df_expenses, budgets, num_months)
        except Exception as e:
            st.error(f"Failed to display overview: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Transactions tab
    with tabs[1]:
        try:
            render_transactions_tab(df_filtered)
        except Exception as e:
            st.error(f"Failed to display transactions: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Budgets tab
    with tabs[2]:
        try:
            render_budgets_tab(df_expenses, budgets, num_months)
        except Exception as e:
            st.error(f"Failed to display budgets: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Insights tab
    with tabs[3]:
        try:
            render_insights_tab(df_expenses)
        except Exception as e:
            st.error(f"Failed to display insights: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Sankey (Cash Flow) tab
    with tabs[4]:
        try:
            render_sankey_tab(df_filtered)
        except Exception as e:
            st.error(f"Failed to display cash flow diagram: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)