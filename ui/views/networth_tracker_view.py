"""Main networth tracker view coordinator.

This module manages the networth tracker interface and coordinates between different views.
"""

import streamlit as st
from ui.views.networth_tracker.growth_over_time import show_growth_over_time
from ui.views.networth_tracker.pivot_table import show_pivot_table
from ui.views.networth_tracker.dashboard import render_dashboard
from ui.views.networth_tracker.growth_projections import show_growth_projections
# from views.networth_tabs.explorer import get_pyg_renderer
from typing import Optional
from pygwalker.api.streamlit import StreamlitRenderer

@st.cache_resource
def get_pyg_renderer(data) -> Optional[StreamlitRenderer]:
    """Initialize PyGWalker renderer with caching.
    
    Args:
        data: DataFrame to visualize
        
    Returns:
        StreamlitRenderer instance or None if initialization fails
    """
    try:
        return StreamlitRenderer(data, spec_io_mode="rw")
    except Exception as e:
        st.error(f"Failed to initialize data explorer: {str(e)}")
        return None


def show_networth_tracker(df_filtered, data):
    """
    Display the networth tracker interface with multiple tabs.
    
    This function orchestrates data loading, filtering, and tab rendering
    for the networth tracking application.
    
    Returns:
        None
    """

    # Tab names for Net Worth Tracker
    TAB_GROWTH = "Net Worth Over Time"
    TAB_TABLE = "Summarized Table"
    TAB_DASHBOARD = "Dashboard"
    TAB_PROJECTIONS = "Growth Projections"
    TAB_EXPLORER = "Data Explorer"


    # Create tabs
    tabs = st.tabs([TAB_GROWTH, TAB_TABLE, TAB_DASHBOARD, TAB_PROJECTIONS, TAB_EXPLORER])
    
    with tabs[0]:
        try:
            show_growth_over_time(df_filtered)
        except Exception as e:
            st.error(f"Failed to display growth chart: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    with tabs[1]:
        try:
            show_pivot_table(df_filtered)
        except Exception as e:
            st.error(f"Failed to display pivot table: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    with tabs[2]:
        try:
            render_dashboard(df_filtered)
        except Exception as e:
            st.error(f"Failed to display dashboard: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)

    with tabs[3]:
        try:
            show_growth_projections(df_filtered)
        except Exception as e:
            st.error(f"Failed to display projections: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)

    with tabs[4]:
        try:
            renderer = get_pyg_renderer(data)
            if renderer:
                renderer.explorer()
            else:
                st.warning("Data explorer is not available.")
        except Exception as e:
            st.error(f"Failed to display data explorer: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)