"""Main application entry point for Personal Finance Tracker.

This module serves as the main entry point for the Personal Finance Tracker application,
handling navigation between Net Worth Tracker and Expense Tracker views.
"""

from typing import Optional

import streamlit as st
from pygwalker.api.streamlit import StreamlitRenderer

from data.loader import load_networth_data, load_expense_transactions, load_budgets
from data.filters import filter_data, get_filtered_accounts
from data.calculations import calculate_account_info
from ui.components.filters import (
    render_networth_header_filters,
    render_networth_sidebar_filters,
    render_expense_date_filter
)
from ui.views.networth_tracker_view import show_networth_tracker 
from ui.views.expense_tracker_view import show_expense_tracker

# Constants
APP_TITLE = "Personal Finance Tracker"
PAGE_ICON = "💰"
LAYOUT = "wide"

# Navigation options
NAV_NETWORTH = "Net Worth Tracker"
NAV_EXPENSE = "Expense Tracker"


def render_networth_tracker() -> None:
    """Render the Net Worth Tracker view with error handling."""
    try:
        # Load data
        data = load_networth_data()
        
        if data is None or data.empty:
            st.warning("No net worth data available. Please check your data source.")
            return

        # Render header filters
        selected_account_types, selected_categories = render_networth_header_filters(data)
        
        if not selected_account_types or not selected_categories:
            st.info("Please select at least one account_type and category to view data.")
            return
        
        # Get filtered account list
        accounts = get_filtered_accounts(data, selected_account_types, selected_categories)
        
        if not accounts:
            st.warning("No accounts match the selected filters.")
            return
        
        # Calculate account info for sidebar
        account_info = calculate_account_info(data, accounts)
        
        # Render sidebar filters
        selected_accounts = render_networth_sidebar_filters(data, accounts, account_info)
        
        if not selected_accounts:
            st.warning("No accounts selected. Please select at least one account to view data.")
            return
        
        # Apply all filters
        filtered_df = filter_data(data, selected_account_types, selected_categories, selected_accounts)
        
        if filtered_df.empty:
            st.warning("No data available for the selected filters.")
            return
        
        show_networth_tracker(filtered_df, data)
                  
    except Exception as e:
        st.error(f"An error occurred while loading the Net Worth Tracker: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def render_expense_tracker() -> None:
    """Render the Expense Tracker view with error handling."""
    try:
        # Load data
        df = load_expense_transactions()
        budgets = load_budgets()
        
        if df is None or df.empty:
            st.warning(" No expense data available. Please check your data source.")
            return
        
        # Render date filter in sidebar and get filtered data
        df_filtered, num_months, date_range_days = render_expense_date_filter(df)
        
        if df_filtered.empty:
            st.warning(" No expenses found for the selected date range.")
            return
        
        # Show expense tracker with filtered data
        show_expense_tracker(df_filtered, budgets, num_months)
        
    except Exception as e:
        st.error(f" An error occurred while loading the Expense Tracker: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def main() -> None:
    """Main application function with error handling and navigation."""
    try:
        # Page configuration
        st.set_page_config(
            page_title=APP_TITLE,
            page_icon=PAGE_ICON,
            layout=LAYOUT
        )
        
        # Sidebar navigation
        st.sidebar.title("Navigation")
        app_mode = st.sidebar.radio(
            "Select View",
            [NAV_NETWORTH, NAV_EXPENSE],
            help="Choose between Net Worth tracking and Expense tracking"
        )
        
        st.sidebar.markdown("---")
        
        # Header
        st.header(APP_TITLE)
        
        # Route to appropriate view
        if app_mode == NAV_NETWORTH:
            render_networth_tracker()
        elif app_mode == NAV_EXPENSE:
            render_expense_tracker()
        else:
            st.error(f" Unknown view selected: {app_mode}")
            
    except Exception as e:
        st.error(" A critical error occurred. Please refresh the page or contact support.")
        with st.expander("Error Details"):
            st.exception(e)


if __name__ == "__main__":
    main()