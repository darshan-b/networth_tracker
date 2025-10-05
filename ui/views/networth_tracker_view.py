"""Main networth tracker view coordinator.

This module manages the networth tracker interface and coordinates between different views,
including growth charts, pivot tables, dashboards, projections, and data exploration.
"""

import streamlit as st
import pandas as pd
from typing import Optional
from pygwalker.api.streamlit import StreamlitRenderer

from constants import ColumnNames
from data.validators import validate_dataframe
from ui.components.utils import safe_render_tab, render_empty_state
from ui.views.networth_tracker.growth_over_time import show_growth_over_time
from ui.views.networth_tracker.pivot_table import show_pivot_table
from ui.views.networth_tracker.dashboard import render_dashboard
from ui.views.networth_tracker.growth_projections import show_growth_projections


# Tab configuration
TAB_NAMES = [
    "Net Worth Over Time",
    "Summarized Table",
    "Dashboard",
    "Growth Projections",
    "Data Explorer"
]


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


def show_networth_tracker(
    df_filtered: Optional[pd.DataFrame],
    data: Optional[pd.DataFrame]
) -> None:
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
    """
    # Validate main dataset
    required_columns = [
        ColumnNames.MONTH,
        ColumnNames.MONTH_STR,
        ColumnNames.AMOUNT,
        ColumnNames.ACCOUNT_TYPE
    ]
    
    if not validate_dataframe(df_filtered, required_columns, context="networth data"):
        render_empty_state(
            title="No Networth Data",
            message="No networth data available for the selected period.",
            show_tips=True,
            tips=[
                "Check your date range filter",
                "Ensure networth data has been loaded",
                "Verify your data file contains the required columns"
            ]
        )
        return
    
    # Check explorer data (non-blocking)
    explorer_available = validate_dataframe(data, min_rows=1, context="")
    
    # Create navigation tabs
    tabs = st.tabs(TAB_NAMES)
    
    # Render Net Worth Over Time tab
    with tabs[0]:
        safe_render_tab(
            show_growth_over_time,
            df_filtered,
            error_context="growth chart"
        )
    
    # Render Summarized Table tab
    with tabs[1]:
        safe_render_tab(
            show_pivot_table,
            df_filtered,
            error_context="pivot table"
        )
    
    # Render Dashboard tab
    with tabs[2]:
        safe_render_tab(
            render_dashboard,
            df_filtered,
            error_context="dashboard"
        )
    
    # Render Growth Projections tab
    with tabs[3]:
        safe_render_tab(
            show_growth_projections,
            df_filtered,
            error_context="projections"
        )
    
    # Render Data Explorer tab
    with tabs[4]:
        safe_render_tab(
            _render_data_explorer,
            data if explorer_available else None,
            error_context="data explorer"
        )


def _render_data_explorer(data: Optional[pd.DataFrame]) -> None:
    """
    Render the data explorer tab with PyGWalker.
    
    Args:
        data: DataFrame to explore, or None if unavailable
    """
    if data is None or data.empty:
        st.warning("Data explorer is not available - no data provided.")
        st.info("The data explorer requires the complete unfiltered dataset.")
        return
    
    renderer = get_pyg_renderer(data)
    
    if renderer:
        renderer.explorer()
    else:
        st.warning("Data explorer could not be initialized.")
        st.info("Try refreshing the page or check your data format.")
