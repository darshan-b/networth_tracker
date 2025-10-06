"""Reusable UI components and patterns."""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Callable, Any
from functools import wraps


def render_metric_cards(metrics_config: Dict[str, Dict[str, Any]], num_columns: Optional[int] = None) -> None:
    """
    Render multiple metrics in columns dynamically.
    
    Args:
        metrics_config: Dictionary where keys are metric identifiers and values are dicts
                       containing 'label', 'value', and optional 'delta', 'delta_color'
        num_columns: Number of columns to create (defaults to number of metrics)
        
    Example:
        metrics_config = {
            'net_worth': {'label': 'Net Worth', 'value': '$100,000', 'delta': '+5%'},
            'total_assets': {'label': 'Assets', 'value': '$150,000'}
        }
        render_metric_cards(metrics_config)
    """
    num_columns = num_columns or len(metrics_config)
    cols = st.columns(num_columns)
    
    for idx, (metric_id, config) in enumerate(metrics_config.items()):
        col_idx = idx % num_columns
        with cols[col_idx]:
            st.metric(
                label=config['label'],
                value=config['value'],
                delta=config.get('delta'),
                delta_color=config.get('delta_color', 'normal')
            )


def render_summary_statistics(
    stats: Dict[str, Any],
    num_columns: int = 3,
    formatter: Optional[Callable] = None
) -> None:
    """
    Render summary statistics in a grid layout.
    
    Args:
        stats: Dictionary of stat_name: value pairs
        num_columns: Number of columns in the grid
        formatter: Optional function to format values (default: str)
    """
    formatter = formatter or str
    cols = st.columns(num_columns)
    
    for idx, (label, value) in enumerate(stats.items()):
        col_idx = idx % num_columns
        with cols[col_idx]:
            st.metric(label, formatter(value))


def render_filter_row(
    filters_config: List[Dict[str, Any]],
    key_prefix: str = ""
) -> Dict[str, Any]:
    """
    Render a row of filters and return selected values.
    
    Args:
        filters_config: List of filter configurations, each containing:
            - 'type': 'selectbox', 'multiselect', 'text_input', etc.
            - 'label': Filter label
            - 'options': Options for select widgets
            - 'default': Default value
            - 'key': Unique key (optional, will be generated if not provided)
        key_prefix: Prefix for widget keys to avoid collisions
        
    Returns:
        Dictionary mapping filter labels to selected values
        
    Example:
        filters_config = [
            {'type': 'selectbox', 'label': ColumnNames.DATE, 'options': ['All', 'Food', 'Gas']},
            {'type': 'text_input', 'label': 'Search', 'default': ''}
        ]
        selections = render_filter_row(filters_config)
    """
    cols = st.columns(len(filters_config))
    selections = {}
    
    for idx, filter_cfg in enumerate(filters_config):
        with cols[idx]:
            filter_type = filter_cfg['type']
            label = filter_cfg['label']
            key = filter_cfg.get('key', f"{key_prefix}_{label.lower().replace(' ', '_')}")
            
            if filter_type == 'selectbox':
                selections[label] = st.selectbox(
                    label,
                    options=filter_cfg.get('options', []),
                    index=filter_cfg.get('index', 0),
                    key=key
                )
            elif filter_type == 'multiselect':
                selections[label] = st.multiselect(
                    label,
                    options=filter_cfg.get('options', []),
                    default=filter_cfg.get('default', filter_cfg.get('options', [])),
                    key=key
                )
            elif filter_type == 'text_input':
                selections[label] = st.text_input(
                    label,
                    value=filter_cfg.get('default', ''),
                    key=key
                )
            elif filter_type == 'number_input':
                selections[label] = st.number_input(
                    label,
                    min_value=filter_cfg.get('min_value', 0),
                    max_value=filter_cfg.get('max_value', None),
                    value=filter_cfg.get('default', 0),
                    step=filter_cfg.get('step', 1),
                    key=key
                )
    
    return selections


def safe_render_tab(render_func: Callable, *args, error_context: str = "this view", **kwargs) -> None:
    """
    Wrapper for rendering tab content with consistent error handling.
    
    Args:
        render_func: Function to call for rendering
        *args: Positional arguments to pass to render_func
        error_context: Description of what's being rendered for error messages
        **kwargs: Keyword arguments to pass to render_func
        
    Example:
        with tabs[0]:
            safe_render_tab(render_overview_tab, df, budgets, error_context="overview")
    """
    try:
        render_func(*args, **kwargs)
    except Exception as e:
        st.error(f"Failed to display {error_context}: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def render_info_message(
    message: str,
    message_type: str = "info",
    icon: Optional[str] = None
) -> None:
    """
    Render an informational message with consistent styling.
    
    Args:
        message: Message text to display
        message_type: Type of message ('info', 'warning', 'error', 'success')
        icon: Optional icon to display
    """
    message_func = {
        'info': st.info,
        'warning': st.warning,
        'error': st.error,
        'success': st.success
    }.get(message_type, st.info)
    
    message_func(message, icon=icon)


def render_empty_state(
    title: str = "No Data Available",
    message: str = "Please adjust your filters or add data.",
    show_tips: bool = False,
    tips: Optional[List[str]] = None
) -> None:
    """
    Render a helpful empty state when no data is available.
    
    Args:
        title: Title for the empty state
        message: Main message to display
        show_tips: Whether to show helpful tips
        tips: List of tip strings to display
    """
    st.warning(title)
    st.info(message)
    
    if show_tips and tips:
        with st.expander("💡 Tips"):
            for tip in tips:
                st.markdown(f"- {tip}")


def create_download_button(
    data: Any,
    filename: str,
    button_label: str = "Download",
    mime_type: str = "text/csv"
) -> None:
    """
    Create a download button with consistent styling.
    
    Args:
        data: Data to download (string, bytes, or buffer)
        filename: Name of the downloaded file
        button_label: Label for the download button
        mime_type: MIME type of the file
    """
    st.download_button(
        label=button_label,
        data=data,
        file_name=filename,
        mime=mime_type
    )


def render_tabs_safely(
    tab_configs: List[Dict[str, Any]],
    tab_names: List[str]
) -> None:
    """
    Render multiple tabs with consistent error handling.
    
    Args:
        tab_configs: List of dicts with 'render_func', 'args', 'kwargs', 'context'
        tab_names: List of tab names
        
    Example:
        tab_configs = [
            {
                'render_func': render_overview_tab,
                'args': [df, budgets],
                'kwargs': {'num_months': 1},
                'context': 'overview'
            },
            ...
        ]
        render_tabs_safely(tab_configs, ['Overview', 'Transactions'])
    """
    tabs = st.tabs(tab_names)
    
    for idx, (tab, config) in enumerate(zip(tabs, tab_configs)):
        with tab:
            safe_render_tab(
                config['render_func'],
                *config.get('args', []),
                error_context=config.get('context', f'tab {idx}'),
                **config.get('kwargs', {})
            )


def render_period_badge(num_periods: int, period_type: str = "month") -> None:
    """
    Render a badge showing the number of periods in the analysis.
    
    Args:
        num_periods: Number of periods
        period_type: Type of period (ColumnNames.MONTH, 'quarter', 'year')
    """
    period_plural = f"{period_type}s" if num_periods != 1 else period_type
    
    if num_periods == 1:
        st.info(f"Showing data for 1 {period_type}")
    else:
        st.info(f"Showing data for {num_periods} {period_plural}")