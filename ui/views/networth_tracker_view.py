"""Main networth tracker view coordinator.

This module manages the networth tracker interface and coordinates between different views,
including growth charts, pivot tables, dashboards, projections, and data exploration.
"""

import streamlit as st
import pandas as pd
from typing import Optional
from pygwalker.api.streamlit import StreamlitRenderer

from ui.views.networth_tracker.growth_over_time import show_growth_over_time
from ui.views.networth_tracker.pivot_table import show_pivot_table
from ui.views.networth_tracker.dashboard import render_dashboard
from ui.views.networth_tracker.growth_projections import show_growth_projections


# Tab name constants
TAB_GROWTH = "Net Worth Over Time"
TAB_TABLE = "Summarized Table"
TAB_DASHBOARD = "Dashboard"
TAB_PROJECTIONS = "Growth Projections"
TAB_EXPLORER = "Data Explorer"


@st.cache_resource
def get_pyg_renderer(data: pd.DataFrame) -> Optional[StreamlitRenderer]:
    """
    Initialize PyGWalker renderer with caching for data exploration.
    
    This function creates a StreamlitRenderer instance for interactive data exploration
    using PyGWalker. Results are cached to avoid re-initialization on reruns.
    
    Args:
        data: DataFrame to visualize in the data explorer.
        
    Returns:
        StreamlitRenderer instance if initialization succeeds, None otherwise.
        
    Note:
        Uses spec_io_mode="rw" to allow saving and loading visualization specifications.
    """
    try:
        return StreamlitRenderer(data, spec_io_mode="rw")
    except Exception as e:
        st.error(f"Failed to initialize data explorer: {str(e)}")
        return None


def show_networth_tracker(df_filtered: Optional[pd.DataFrame], data: Optional[pd.DataFrame]) -> None:
    """
    Display the networth tracker interface with multiple tabs.
    
    This function orchestrates data loading, filtering, and tab rendering
    for the networth tracking application.
    
    Args:
        df_filtered: Filtered networth dataframe for time-series analysis.
                    Should contain date, account, and balance information.
        data: Complete unfiltered dataset for data exploration tab.
             Used by PyGWalker for interactive analysis.
        
    Returns:
        None
        
    Raises:
        Does not raise exceptions directly, but displays error messages to the UI
        when invalid inputs are detected or rendering errors occur.
    """
    # Validate inputs
    if df_filtered is None or df_filtered.empty:
        st.warning("No networth data available for the selected period.")
        return
    
    if data is None or data.empty:
        st.warning("No data available for the data explorer.")
        # Continue with other tabs even if data explorer won't work
    
    # Create navigation tabs
    tabs = st.tabs([
        TAB_GROWTH,
        TAB_TABLE,
        TAB_DASHBOARD,
        TAB_PROJECTIONS,
        TAB_EXPLORER
    ])
    
    # Render Net Worth Over Time tab
    with tabs[0]:
        try:
            show_growth_over_time(df_filtered)
        except Exception as e:
            st.error(f"Failed to display growth chart: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Summarized Table tab
    with tabs[1]:
        try:
            show_pivot_table(df_filtered)
        except Exception as e:
            st.error(f"Failed to display pivot table: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Dashboard tab
    with tabs[2]:
        try:
            render_dashboard(df_filtered)
        except Exception as e:
            st.error(f"Failed to display dashboard: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Growth Projections tab
    with tabs[3]:
        try:
            show_growth_projections(df_filtered)
        except Exception as e:
            st.error(f"Failed to display projections: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)
    
    # Render Data Explorer tab
    with tabs[4]:
        try:
            if data is None or data.empty:
                st.warning("Data explorer is not available - no data provided.")
            else:
                renderer = get_pyg_renderer(data)
                if renderer:
                    renderer.explorer()
                else:
                    st.warning("Data explorer could not be initialized.")
        except Exception as e:
            st.error(f"Failed to display data explorer: {str(e)}")
            with st.expander("Error Details"):
                st.exception(e)