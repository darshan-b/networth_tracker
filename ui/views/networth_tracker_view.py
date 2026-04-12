"""Main networth tracker view coordinator.

This module manages the networth tracker interface and coordinates between different views,
including growth charts, pivot tables, dashboards, projections, and data exploration.
"""

import streamlit as st
import pandas as pd
from typing import Optional
from pygwalker.api.streamlit import StreamlitRenderer

from config import NetWorthConfig
from constants import ColumnNames
from data.validators import validate_dataframe
from ui.components.utils import render_empty_state, render_tabs_safely
from ui.views.networth_tracker.growth_over_time import show_growth_over_time
from ui.views.networth_tracker.pivot_table import show_pivot_table
from ui.views.networth_tracker.dashboard import render_dashboard
from ui.views.networth_tracker.growth_projections import show_growth_projections


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
    
    tab_configs = [
        {
            'render_func': show_growth_over_time,
            'args': [df_filtered],
            'context': 'growth chart',
        },
        {
            'render_func': show_pivot_table,
            'args': [df_filtered],
            'context': 'pivot table',
        },
        {
            'render_func': render_dashboard,
            'args': [df_filtered],
            'context': 'dashboard',
        },
        {
            'render_func': show_growth_projections,
            'args': [df_filtered],
            'context': 'projections',
        },
        {
            'render_func': _render_data_explorer,
            'args': [data if explorer_available else None],
            'context': 'data explorer',
        },
    ]

    render_tabs_safely(tab_configs, NetWorthConfig.TAB_NAMES)


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
