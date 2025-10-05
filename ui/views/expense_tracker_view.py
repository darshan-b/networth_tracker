"""Main expense tracker view coordinator.

This module manages the expense tracker interface and coordinates between different tab views.
Transactions are stored with negative amounts for expenses and positive for income.
Income is identified by category == 'Income'.
"""

import streamlit as st
from data.filters import filter_expenses
from ui.views.expense_tracker.overview import render_overview_tab
from ui.views.expense_tracker.transactions import render_transactions_tab
from ui.views.expense_tracker.budget import render_budgets_tab
from ui.views.expense_tracker.insights import render_insights_tab
from ui.views.expense_tracker.sankey import render_sankey_tab


def show_expense_tracker(df_filtered, budgets, num_months=1):
    """
    Display the expense tracker interface with multiple tabs.
    
    Args:
        df_filtered (pd.DataFrame): Filtered transactions dataframe
        budgets (dict): Dictionary of monthly budgets by category
        num_months (int): Number of distinct months in the selected date range
        
    Returns:
        None
    """
    if df_filtered is None or df_filtered.empty:
        st.warning("No transaction data available for the selected period.")
        return
    
    if not isinstance(budgets, dict):
        st.error("Invalid budget configuration. Please check your budget data.")
        return
    
    st.divider()
    
    # Create navigation tabs
    tab_overview, tab_transactions, tab_budgets, tab_insights, tab_sankey = st.tabs([
        "Overview", 
        "Transactions", 
        "Budgets", 
        "Insights",
        "Cash Flow"
    ])
    
    # Filter for expenses (for tabs that only need expense data)
    df_expenses = filter_expenses(df_filtered)
    
    # Render each tab
    with tab_overview:
        render_overview_tab(df_expenses, budgets, num_months)
    
    with tab_transactions:
        render_transactions_tab(df_filtered)
    
    with tab_budgets:
        render_budgets_tab(df_expenses, budgets, num_months)
    
    with tab_insights:
        render_insights_tab(df_expenses)
    
    with tab_sankey:
        render_sankey_tab(df_filtered)
