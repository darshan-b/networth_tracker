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
from pygwalker.api.streamlit import StreamlitRenderer


def main():
    """Main application function."""
    # Page configuration
    st.set_page_config(page_title="Net Worth Tracker", layout="wide")
    
    # Load data
    data = load_data()
    
    # Header
    st.header("Net Worth Tracker")
    
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
    
    # Create tabs
    tab_1, tab_2, tab_combined, tab_4, tab_5 = st.tabs(["Net Worth Over Time", "Summarized Table", "Dashboard", "Growth Projections", "Data Explorer"])
    
    @st.cache_resource
    def get_pyg_renderer() -> "StreamlitRenderer":
        # If you want to use feature of saving chart config, set `spec_io_mode="rw"`
        return StreamlitRenderer(data, spec_io_mode="rw")


    with tab_1:
        show_growth_over_time(filtered_df)
    
    with tab_2:
        show_pivot_table(filtered_df)
    
    with tab_combined:
        render_dashboard(filtered_df)

    with tab_4:
        show_growth_projections(filtered_df)

    with tab_5:
        renderer = get_pyg_renderer()
        renderer.explorer()





if __name__ == "__main__":
    main()