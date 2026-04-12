"""Main application entry point for Personal Finance Tracker.

This module serves as the main entry point for the Personal Finance Tracker application,
handling navigation between Net Worth Tracker, Expense Tracker, and Stock Tracker views.
"""

import streamlit as st

from config import AppConfig
from app_constants import ColumnNames
from data.loader import (
    load_networth_data, 
    load_expense_transactions, 
    load_budgets, 
    load_stock_data
)
from data.filters import filter_data, get_filtered_accounts
from data.calculations import calculate_account_info
from ui.components.filters import (
    render_networth_header_filters,
    render_networth_sidebar_filters,
    render_expense_date_filter
)
from ui.components.utils import render_recovery_guide
from ui.views.networth_tracker_view import show_networth_tracker 
from ui.views.expense_tracker_view import show_expense_tracker
from ui.views.stock_tracker_view import show_stock_tracker

def render_app_intro() -> None:
    """Render top-level guidance for first-time use."""
    with st.expander(AppConfig.GETTING_STARTED_TITLE, expanded=False):
        for step in AppConfig.GETTING_STARTED_STEPS:
            st.markdown(f"- {step}")


def render_networth_tracker() -> None:
    """Render the Net Worth Tracker view with error handling."""
    try:
        # Load data
        data = load_networth_data()
        
        if data is None or data.empty:
            render_recovery_guide(
                "Net worth data is not available.",
                "The tracker could not find usable net worth data for this view.",
                [
                    "Confirm `data/raw/Networth.csv` exists.",
                    "Check that the file includes `account_type`, `account_subtype`, `financial_institution`, `account_number`, `as_of_date`, and `balance` columns.",
                    "Refresh the app after updating the file."
                ]
            )
            return

        duplicate_account_names = (
            data[ColumnNames.ACCOUNT].duplicated(keep=False).any()
            if ColumnNames.ACCOUNT in data.columns
            else False
        )
        has_account_id = (
            ColumnNames.ACCOUNT_ID in data.columns
            and data[ColumnNames.ACCOUNT_ID].fillna("").astype(str).str.strip().ne("").any()
        )

        if duplicate_account_names and not has_account_id:
            st.warning(
                "Duplicate account names were found without a unique account identifier. "
                "Selections may still merge similarly named accounts."
            )
            st.caption(
                "Add an `account_number`, `account_id`, or similar unique column to your net worth source file "
                "so the tracker can distinguish accounts with the same display name."
            )

        # Render header filters
        selected_account_types, selected_categories = render_networth_header_filters(data)
        
        if not selected_account_types or not selected_categories:
            render_recovery_guide(
                "Choose at least one filter value.",
                "Net worth charts need at least one account type and one account subtype selected.",
                [
                    "Re-select one or more account types in the header.",
                    "Re-select one or more account subtypes in the header.",
                    "If no options appear, verify the source data contains those columns."
                ],
                message_type="info"
            )
            return
        
        # Get filtered account list
        accounts = get_filtered_accounts(data, selected_account_types, selected_categories)
        
        if not accounts:
            render_recovery_guide(
                "No accounts match the current filters.",
                "The selected account types and account subtypes did not produce any matching accounts.",
                [
                    "Broaden the account type or account subtype filters.",
                    "Check whether the selected combination exists in your source data."
                ]
            )
            return
        
        # Calculate account info for sidebar
        account_info = calculate_account_info(data, accounts)
        
        # Render sidebar filters
        selected_accounts = render_networth_sidebar_filters(data, accounts, account_info)
        
        if not selected_accounts:
            render_recovery_guide(
                "No accounts are selected.",
                "Select at least one account from the sidebar to render the net worth views.",
                [
                    "Use `Select All` in the sidebar to restore all accounts.",
                    "Clear the sidebar search if it is hiding results."
                ]
            )
            return
        
        # Apply all filters
        filtered_df = filter_data(data, selected_account_types, selected_categories, selected_accounts)
        
        if filtered_df.empty:
            render_recovery_guide(
                "No data is available for these filters.",
                "The current filter combination removed all rows from the net worth dataset.",
                [
                    "Broaden the selected account types, categories, or accounts.",
                    "Check whether your source data contains rows for the expected period."
                ],
                message_type="info"
            )
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
            render_recovery_guide(
                "Expense data is not available.",
                "The expense tracker could not find usable transaction data.",
                [
                    "Confirm `data/raw/transactions.xlsx` exists.",
                    "Check that the file includes `date`, `amount`, `category`, `merchant`, and `account` columns.",
                    "Refresh the app after updating the file."
                ]
            )
            return
        
        # Render date filter in sidebar and get filtered data
        df_filtered, num_months, date_range_days = render_expense_date_filter(df)
        
        if df_filtered.empty:
            render_recovery_guide(
                "No expenses were found for this date range.",
                "The selected period does not contain any matching transaction rows.",
                [
                    "Expand the date range.",
                    "Verify that your transaction file contains rows in the selected period."
                ],
                message_type="info"
            )
            return
        
        # Show expense tracker with filtered data
        show_expense_tracker(df_filtered, budgets, num_months)
        
    except Exception as e:
        st.error(f"An error occurred while loading the Expense Tracker: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def render_stock_tracker() -> None:
    """Render the Stock Tracker view with error handling."""
    try:
        # Load only historical and trading_log - no summary or tracking needed
        trading_log, historical = load_stock_data()
        
        if historical is None or historical.empty:
            render_recovery_guide(
                "Stock history is not available.",
                "The stock tracker could not find usable historical data to analyze.",
                [
                    "Confirm `data/raw/stock_positions.xlsx` exists.",
                    "Check that the workbook includes a `Historical_Tracking` sheet.",
                    "Verify the sheet has `Date`, `ticker` or `Symbol`, `quantity`, `Brokerage`, `Account Name`, and `Investment Type`."
                ],
                message_type="error"
            )
            return
        
        show_stock_tracker(trading_log, historical)
        
    except Exception as e:
        st.error(f"An error occurred while loading the Stock Tracker: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def main() -> None:
    """Main application function with error handling and navigation."""
    try:
        # Page configuration
        st.set_page_config(
            page_title=AppConfig.TITLE,
            page_icon=AppConfig.PAGE_ICON,
            layout=AppConfig.LAYOUT
        )
    
        # Sidebar navigation
        st.sidebar.title(AppConfig.NAVIGATION_TITLE)
        app_mode = st.sidebar.radio(
            AppConfig.VIEW_SELECTOR_LABEL,
            AppConfig.VIEW_OPTIONS,
            help=AppConfig.VIEW_HELP
        )
    
        st.sidebar.markdown("---")
    
        # Header
        st.header(AppConfig.TITLE)
        render_app_intro()
    
        # Route to appropriate view
        if app_mode == AppConfig.VIEW_OPTIONS[0]:
            render_networth_tracker()
        elif app_mode == AppConfig.VIEW_OPTIONS[1]:
            render_expense_tracker()
        elif app_mode == AppConfig.VIEW_OPTIONS[2]:
            render_stock_tracker()
        else:
            st.error(f"Unknown view selected: {app_mode}")
    
    except Exception as e:
        st.error("A critical error occurred. Please refresh the page or contact support.")
        with st.expander("Error Details"):
            st.exception(e)


if __name__ == "__main__":
    main()
