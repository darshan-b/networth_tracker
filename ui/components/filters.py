"""UI components for filters in the Personal Finance Tracker.

This module handles all user interface components for filtering data in both
Net Worth and Expense tracking views, with comprehensive error handling.
"""

from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

from data.filters import (
    get_date_range_options,
    calculate_date_range,
    filter_by_date_range,
    DATE_RANGE_CUSTOM
)

# Constants
MIN_ACCOUNTS_WARNING = 0
DEFAULT_EXPANDER_STATE = True
SEARCH_PLACEHOLDER = "Type to filter..."


def render_networth_header_filters(data: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """Render account_type and category segmented controls for Net Worth Tracker.
    
    Args:
        data: Full dataset
        
    Returns:
        Tuple of (selected_account_types, selected_categories)
        
    Raises:
        ValueError: If data is invalid
    """
    try:        
        required_columns = ['account_type', 'category']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            st.error(f" Data is missing required columns: {', '.join(missing_columns)}")
            return [], []
        
        # Render account_type filter
        acct_types = sorted(data['account_type'].unique())
        
        if not acct_types:
            st.warning(" No account_types found in data.")
            return [], []
        
        selected_account_types = st.segmented_control(
            "account_type", 
            options=acct_types, 
            selection_mode="multi", 
            default=acct_types,
            help="Filter by account_type (e.g., Checking, Savings, Investment)"
        )
        
        # Render category filter based on selected account_types
        if selected_account_types:
            categories = sorted(data[data['account_type'].isin(selected_account_types)]['category'].unique())
        else:
            categories = sorted(data['category'].unique())
        
        if not categories:
            st.warning(" No categories available for the selected account_types.")
            return selected_account_types or [], []
        
        selected_categories = st.segmented_control(
            "category", 
            options=categories, 
            selection_mode="multi", 
            default=categories,
            help="Filter by category (e.g., Banking, Retirement, Real Estate)"
        )
        
        return selected_account_types or [], selected_categories or []
        
    except Exception as e:
        st.error(f" Error rendering filters: {str(e)}")
        return [], []


def render_networth_sidebar_filters(data: pd.DataFrame, accounts: List[str], account_info: Dict[str, Dict]) -> List[str]:
    """Render sidebar with account selection and search for Net Worth Tracker.
    
    Args:
        data: Full dataset
        accounts: List of available accounts
        account_info: Dictionary with account details (value, trend, type)
        
    Returns:
        List of selected accounts
        
    Raises:
        ValueError: If inputs are invalid
    """
    try:
        st.sidebar.markdown("### account Filter")
        
        # Validate inputs
        if data is None or data.empty:
            st.sidebar.error(" No data available.")
            return []
        
        if not accounts:
            st.sidebar.warning(" No accounts available to display.")
            return []
        
        # Initialize session state
        if 'selected_accounts' not in st.session_state:
            st.session_state.selected_accounts = accounts.copy()
        
        if 'expander_states' not in st.session_state:
            st.session_state.expander_states = {}
        
        # Search box
        search = st.sidebar.text_input(
            "Search accounts",
            "",
            placeholder=SEARCH_PLACEHOLDER,
            help="Filter accounts by name"
        )
        
        # Filter accounts based on search
        if search:
            filtered_accounts = [a for a in accounts if search.lower() in a.lower()]
            if not filtered_accounts:
                st.sidebar.warning(f" No accounts match '{search}'")
        else:
            filtered_accounts = accounts
        
        # Group accounts by type
        grouped_accounts = {}
        for acc in filtered_accounts:
            acct_type = account_info.get(acc, {}).get('type', 'Unknown')
            if acct_type not in grouped_accounts:
                grouped_accounts[acct_type] = []
            grouped_accounts[acct_type].append(acc)
        
        if not grouped_accounts:
            st.sidebar.warning(" No accounts to display.")
            return []
        
        # Initialize expander states for new account_types
        for acct_type in grouped_accounts.keys():
            if acct_type not in st.session_state.expander_states:
                st.session_state.expander_states[acct_type] = DEFAULT_EXPANDER_STATE
        
        # Check if most expanders are expanded
        expanded_count = sum(1 for state in st.session_state.expander_states.values() if state)
        total_count = len(st.session_state.expander_states)
        mostly_expanded = expanded_count > total_count / 2 if total_count > 0 else True
        
        # Quick actions
        col1, col2, col3 = st.sidebar.columns(3)
        with col1:
            if st.button("Select All", use_container_width=True, help="Select all accounts"):
                st.session_state.selected_accounts = accounts.copy()
                st.rerun()
                
        with col2:
            if st.button("Clear All", use_container_width=True, help="Deselect all accounts"):
                st.session_state.selected_accounts = []
                st.rerun()
                
        with col3:
            toggle_label = "Collapse" if mostly_expanded else "Expand"
            if st.button(toggle_label, use_container_width=True, help=f"{toggle_label} all sections"):
                new_state = not mostly_expanded
                for acct_type in grouped_accounts.keys():
                    st.session_state.expander_states[acct_type] = new_state
                st.rerun()
        
        # Grouped display
        for acct_type in sorted(grouped_accounts.keys()):
            accts = grouped_accounts[acct_type]
            is_expanded = st.session_state.expander_states.get(acct_type, DEFAULT_EXPANDER_STATE)
            
            with st.sidebar.expander(f"{acct_type} ({len(accts)})", expanded=is_expanded):
                # Group action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Select All", use_container_width=True, key=f"all_{acct_type}"):
                        current = set(st.session_state.selected_accounts)
                        current.update(accts)
                        st.session_state.selected_accounts = list(current)
                        st.rerun()
                        
                with col2:
                    if st.button("Clear All", use_container_width=True, key=f"none_{acct_type}"):
                        st.session_state.selected_accounts = [
                            a for a in st.session_state.selected_accounts if a not in accts
                        ]
                        st.rerun()
                
                # Individual account checkboxes
                for acc in accts:
                    info = account_info.get(acc, {})
                    value = info.get('value', 0)
                    trend = info.get('trend', '→')
                    label = f"{acc} ({trend} ${value:,.0f})" if info else acc
                    is_selected = acc in st.session_state.selected_accounts
                    
                    if st.checkbox(label, value=is_selected, key=f"check_{acc}"):
                        if acc not in st.session_state.selected_accounts:
                            st.session_state.selected_accounts.append(acc)
                    else:
                        if acc in st.session_state.selected_accounts:
                            st.session_state.selected_accounts.remove(acc)
        
        # Summary statistics
        st.sidebar.divider()
        count = len(st.session_state.selected_accounts)
        total = len(accounts)
        
        if count > MIN_ACCOUNTS_WARNING:
            selected_value = sum(
                account_info.get(a, {}).get('value', 0) 
                for a in st.session_state.selected_accounts
            )
            total_value = sum(
                account_info.get(a, {}).get('value', 0) 
                for a in accounts
            )
            
            # Display selection status
            if count == total:
                st.sidebar.success(f" {count} of {total} selected")
            else:
                st.sidebar.info(f" {count} of {total} selected")
            
            # Display value metrics
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("Selected", f"${selected_value:,.0f}")
            with col2:
                pct = (selected_value / total_value * 100) if total_value != 0 else 0
                st.metric("% of Total", f"{pct:.1f}%")
        else:
            st.sidebar.error(" No accounts selected")
        
        # Search results info
        if search:
            st.sidebar.caption(f"🔍 {len(filtered_accounts)} matches")
        
        return st.session_state.selected_accounts
        
    except Exception as e:
        st.sidebar.error(f" Error rendering account filters: {str(e)}")
        return []


def render_expense_date_filter(df: pd.DataFrame) -> Tuple[pd.DataFrame, int, int]:
    """Render sidebar date range filter for expense tracker.
    
    Args:
        df: Full expense transactions DataFrame
        
    Returns:
        Tuple of (filtered_df, num_months, date_range_days)
        
    Raises:
        ValueError: If DataFrame is invalid
        KeyError: If required columns are missing
    """
    try:
        st.sidebar.markdown("### 📅 Date Range Filter")
        
        # Validate input
        if df is None or df.empty:
            st.sidebar.error(" No expense data available.")
            return pd.DataFrame(), 1, 1
        
        if 'date' not in df.columns:
            st.sidebar.error(" Date information missing from expense data.")
            return pd.DataFrame(), 1, 1
        
        # Date range selector
        date_option = st.sidebar.selectbox(
            "Select Period",
            get_date_range_options(),
            key="global_date_filter",
            help="Choose a predefined date range or select a custom range"
        )
        
        # Handle custom range with UI inputs
        if date_option == DATE_RANGE_CUSTOM:
            col_start, col_end = st.sidebar.columns(2)
            
            with col_start:
                start_date = st.date_input(
                    "Start date",
                    value=df['date'].min().date(),
                    min_value=df['date'].min().date(),
                    max_value=df['date'].max().date(),
                    key="expense_date_start",
                    help="Select the start date for filtering"
                )
            
            with col_end:
                end_date = st.date_input(
                    "End date",
                    value=df['date'].max().date(),
                    min_value=df['date'].min().date(),
                    max_value=df['date'].max().date(),
                    key="expense_date_end",
                    help="Select the end date for filtering"
                )
            
            # Validate custom date range
            if start_date > end_date:
                st.sidebar.warning(" Start date is after end date. Swapping dates.")
                start_date, end_date = end_date, start_date
            
            df_filtered = filter_by_date_range(df, start_date, end_date)
            
        else:
            # Use predefined date range
            date_range = calculate_date_range(date_option)
            
            if date_range:
                start_date, end_date = date_range
                df_filtered = filter_by_date_range(df, start_date, end_date)
            else:
                df_filtered = df.copy()
        
        # Calculate metrics for filtered range
        if len(df_filtered) > 0:
            df_temp = df_filtered.copy()
            df_temp['year_month'] = df_temp['date'].dt.to_period('M')
            num_months = df_temp['year_month'].nunique()
            date_range_days = (df_filtered['date'].max() - df_filtered['date'].min()).days + 1
            
            # Display date range info
            st.sidebar.info(
                f"📊 Showing data from **{df_filtered['date'].min().strftime('%Y-%m-%d')}** "
                f"to **{df_filtered['date'].max().strftime('%Y-%m-%d')}**\n\n"
                f"({date_range_days} days, {num_months} months)"
            )
        else:
            num_months = 1
            date_range_days = 1
            st.sidebar.warning(" No data found in the selected date range.")
        
        return df_filtered, num_months, date_range_days
        
    except Exception as e:
        st.sidebar.error(f" Error applying date filter: {str(e)}")
        return pd.DataFrame(), 1, 1