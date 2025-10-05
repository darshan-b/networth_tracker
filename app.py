"""Main application entry point for Net Worth Tracker."""

import streamlit as st
from data.loader import load_data
from data.filters import filter_data, get_filtered_accounts
from data.calculations import calculate_account_info
from ui.filters import render_header_filters, render_sidebar_filters
from ui.dashboard import render_dashboard
from growth_over_time_view import show_growth_over_time
from pivot_table_view import show_pivot_table
from growth_projections_view import show_growth_projections
from expense_tracker_view import show_expense_tracker
from pygwalker.api.streamlit import StreamlitRenderer
from data.expense_loader import load_transactions, load_budgets
from expense_tracker_view import get_date_range_options, apply_date_filter

def main():
    """Main application function."""
    # Page configuration
    st.set_page_config(page_title="Personal Finance Tracker", layout="wide")
    
    # Load data
    data = load_data()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio(
        "Select View",
        ["📊 Net Worth Tracker", "💳 Expense Tracker"]
    )
    
    st.sidebar.markdown("---")
    
    # Header
    st.header("Personal Finance Tracker")
    
    if app_mode == "📊 Net Worth Tracker":
        # Render header filters
        selected_account_types, selected_categories = render_header_filters(data)
        
        # Get filtered account list
        accounts = get_filtered_accounts(data, selected_account_types, selected_categories)
        
        # Calculate account info for sidebar
        account_info = calculate_account_info(data, accounts)
        
        # Render sidebar filters
        selected_accounts = render_sidebar_filters(data, accounts, account_info)
        
        # Apply all filters
        filtered_df = filter_data(data, selected_account_types, selected_categories, selected_accounts)
        
        # Create tabs for Net Worth Tracker
        tab_1, tab_2, tab_3, tab_4, tab_5 = st.tabs([
            "Net Worth Over Time", 
            "Summarized Table", 
            "Dashboard", 
            "Growth Projections", 
            "Data Explorer"
        ])
        
        @st.cache_resource
        def get_pyg_renderer() -> "StreamlitRenderer":
            # If you want to use feature of saving chart config, set `spec_io_mode="rw"`
            return StreamlitRenderer(data, spec_io_mode="rw")

        with tab_1:
            show_growth_over_time(filtered_df)
        
        with tab_2:
            show_pivot_table(filtered_df)
        
        with tab_3:
            render_dashboard(filtered_df)

        with tab_4:
            show_growth_projections(filtered_df)

        with tab_5:
            renderer = get_pyg_renderer()
            renderer.explorer()
    
    elif app_mode == "💳 Expense Tracker":

        df = load_transactions()
        budgets = load_budgets()
        
        # Global date filter (applies to all tabs)
        # Global date filter in sidebar
        st.sidebar.markdown("### 📅 Date Range Filter")
        
        date_option = st.sidebar.selectbox(
            "Select Period",
            get_date_range_options(),
            key="global_date_filter"
        )
        
        # Apply global date filter
        df_filtered = apply_date_filter(df, date_option, "global")
        
        # Calculate number of distinct months in the filtered range
        if len(df_filtered) > 0:
            df_filtered['year_month'] = df_filtered['date'].dt.to_period('M')
            num_months = df_filtered['year_month'].nunique()
            date_range_days = (df_filtered['date'].max() - df_filtered['date'].min()).days + 1
            # Drop the temporary column
            df_filtered = df_filtered.drop('year_month', axis=1)
        else:
            num_months = 1
            date_range_days = 1
        
        # Display date range info in sidebar
        st.sidebar.info(
            f"📊 Showing data from **{df_filtered['date'].min().strftime('%Y-%m-%d')}** "
            f"to **{df_filtered['date'].max().strftime('%Y-%m-%d')}**\n\n"
            f"({date_range_days} days, {num_months} months)"
        )
        

        show_expense_tracker(df_filtered, budgets, num_months)


if __name__ == "__main__":
    main()