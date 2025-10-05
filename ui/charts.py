"""Centralized chart creation with consistent styling."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List, Dict, Any
from config import ChartConfig, ColorSchemes


def create_bar_chart(
    data: pd.Series,
    title: Optional[str] = None,
    orientation: str = 'h',
    color_scheme: str = 'neutral',
    show_values: bool = True,
    percentage_total: Optional[float] = None,
    **kwargs
) -> go.Figure:
    """
    Create a bar chart with consistent styling.
    
    Args:
        data: Series with labels as index and values
        title: Chart title
        orientation: 'h' for horizontal, 'v' for vertical
        color_scheme: Color scheme name ('assets', 'liabilities', 'neutral', 'categorical')
        show_values: Whether to show value labels on bars
        percentage_total: If provided, show percentages in hover (value/percentage_total*100)
        **kwargs: Additional arguments for layout customization
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    # Select color scheme
    colors = _get_color_scheme(color_scheme, len(data))
    
    # Build trace configuration
    trace_config = {
        'orientation': orientation,
        'marker': dict(
            color=colors,
            line=dict(color=ChartConfig.BAR_LINE_COLOR, width=ChartConfig.BAR_LINE_WIDTH)
        ),
    }
    
    # Set x and y based on orientation
    if orientation == 'h':
        trace_config['x'] = data.values
        trace_config['y'] = data.index
        axis_titles = {'xaxis_title': kwargs.get('x_label', 'amount ($)'), 'yaxis_title': ''}
    else:
        trace_config['x'] = data.index
        trace_config['y'] = data.values
        axis_titles = {'xaxis_title': '', 'yaxis_title': kwargs.get('y_label', 'amount ($)')}
    
    # Add value labels
    if show_values:
        trace_config['text'] = [f'${val:,.0f}' for val in data.values]
        trace_config['textposition'] = 'outside'
        trace_config['textfont'] = dict(size=11)
    
    # Add hover template
    if percentage_total:
        trace_config['hovertemplate'] = (
            '<b>%{' + ('y' if orientation == 'h' else 'x') + '}</b><br>'
            'amount: $%{' + ('x' if orientation == 'h' else 'y') + ':,.0f}<br>'
            'Share: %{customdata:.1f}%<extra></extra>'
        )
        trace_config['customdata'] = [
            val/percentage_total*100 if percentage_total > 0 else 0 
            for val in data.values
        ]
    else:
        trace_config['hovertemplate'] = (
            '<b>%{' + ('y' if orientation == 'h' else 'x') + '}</b><br>'
            'amount: $%{' + ('x' if orientation == 'h' else 'y') + ':,.0f}<extra></extra>'
        )
    
    fig.add_trace(go.Bar(**trace_config))
    
    # Update layout
    layout_config = {
        'height': kwargs.get('height', ChartConfig.HEIGHT),
        'template': ChartConfig.TEMPLATE,
        'font': ChartConfig.FONT,
        'showlegend': False,
        'margin': ChartConfig.MARGIN,
        **axis_titles
    }
    
    if title:
        layout_config['title'] = title
    
    fig.update_layout(**layout_config)
    
    return fig


def create_pie_chart(
    data: pd.Series,
    title: Optional[str] = None,
    hole: float = 0.0,
    color_scheme: str = 'categorical',
    show_legend: bool = True,
    **kwargs
) -> go.Figure:
    """
    Create a pie or donut chart.
    
    Args:
        data: Series with labels as index and values
        title: Chart title
        hole: Size of center hole (0 = pie, 0.4 = donut)
        color_scheme: Color scheme to use
        show_legend: Whether to show the legend
        **kwargs: Additional layout arguments
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    colors = _get_color_scheme(color_scheme, len(data))
    
    fig.add_trace(go.Pie(
        labels=data.index,
        values=data.values,
        hole=hole,
        marker=dict(
            colors=colors,
            line=dict(color='white', width=2)
        ),
        textposition='auto',
        textinfo='label+percent',
        textfont=dict(size=11),
        hovertemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
    ))
    
    layout_config = {
        'height': kwargs.get('height', ChartConfig.HEIGHT),
        'template': ChartConfig.TEMPLATE,
        'font': ChartConfig.FONT,
        'showlegend': show_legend,
        'margin': ChartConfig.MARGIN
    }
    
    if show_legend:
        layout_config['legend'] = dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    
    if title:
        layout_config['title'] = title
    
    fig.update_layout(**layout_config)
    
    return fig


def create_line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
    markers: bool = True,
    **kwargs
) -> go.Figure:
    """
    Create a line chart.
    
    Args:
        data: DataFrame with data
        x: Column name for x-axis
        y: Column name for y-axis
        color: Optional column name for color grouping
        title: Chart title
        markers: Whether to show markers on the line
        **kwargs: Additional arguments
        
    Returns:
        Plotly figure object
    """
    fig = px.line(
        data,
        x=x,
        y=y,
        color=color,
        markers=markers,
        title=title
    )
    
    fig.update_layout(
        height=kwargs.get('height', ChartConfig.HEIGHT),
        template=ChartConfig.TEMPLATE,
        font=ChartConfig.FONT,
        hovermode=ChartConfig.HOVER_MODE,
        margin=ChartConfig.MARGIN
    )
    
    fig.update_traces(
        line_width=kwargs.get('line_width', ChartConfig.LINE_WIDTH),
        marker=dict(size=kwargs.get('marker_size', ChartConfig.MARKER_SIZE))
    )
    
    return fig


def create_stacked_bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    title: Optional[str] = None,
    color_scheme: str = 'categorical',
    **kwargs
) -> go.Figure:
    """
    Create a stacked bar chart.
    
    Args:
        data: DataFrame with data
        x: Column name for x-axis
        y: Column name for y-axis (values)
        color: Column name for color grouping (stack groups)
        title: Chart title
        color_scheme: Color scheme to use
        **kwargs: Additional arguments
        
    Returns:
        Plotly figure object
    """
    fig = px.bar(
        data,
        x=x,
        y=y,
        color=color,
        title=title,
        barmode='stack',
        color_discrete_sequence=_get_color_scheme(color_scheme, data[color].nunique())
    )
    
    fig.update_layout(
        height=kwargs.get('height', ChartConfig.HEIGHT),
        template=ChartConfig.TEMPLATE,
        font=ChartConfig.FONT,
        hovermode=ChartConfig.HOVER_MODE,
        margin=ChartConfig.MARGIN,
        xaxis_title=kwargs.get('x_label', ''),
        yaxis_title=kwargs.get('y_label', 'amount ($)')
    )
    
    return fig


def create_grouped_bar_chart(
    data: pd.DataFrame,
    categories: List[str],
    values_dict: Dict[str, List[float]],
    title: Optional[str] = None,
    colors: Optional[List[str]] = None,
    **kwargs
) -> go.Figure:
    """
    Create a grouped bar chart for comparing multiple series.
    
    Args:
        data: DataFrame or None (values_dict will be used)
        categories: List of category names for x-axis
        values_dict: Dictionary of {series_name: [values]} for each bar group
        title: Chart title
        colors: List of colors for each series
        **kwargs: Additional arguments
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    if colors is None:
        colors = ColorSchemes.CATEGORICAL[:len(values_dict)]
    
    for idx, (name, values) in enumerate(values_dict.items()):
        fig.add_trace(go.Bar(
            name=name,
            x=categories,
            y=values,
            marker_color=colors[idx] if idx < len(colors) else ColorSchemes.PRIMARY
        ))
    
    fig.update_layout(
        barmode='group',
        height=kwargs.get('height', ChartConfig.HEIGHT),
        template=ChartConfig.TEMPLATE,
        font=ChartConfig.FONT,
        margin=ChartConfig.MARGIN,
        xaxis_title=kwargs.get('x_label', ''),
        yaxis_title=kwargs.get('y_label', 'amount ($)'),
        title=title
    )
    
    return fig


def _get_color_scheme(scheme_name: str, num_colors: int) -> List[str]:
    """
    Get a color scheme by name.
    
    Args:
        scheme_name: Name of the color scheme
        num_colors: Number of colors needed
        
    Returns:
        List of color codes
    """
    schemes = {
        'assets': ColorSchemes.ASSETS,
        'liabilities': ColorSchemes.LIABILITIES,
        'neutral': ColorSchemes.NEUTRAL,
        'categorical': ColorSchemes.CATEGORICAL
    }
    
    colors = schemes.get(scheme_name, ColorSchemes.NEUTRAL)
    
    # Extend colors if needed by repeating
    while len(colors) < num_colors:
        colors = colors + colors
    
    return colors[:num_colors]


# Legacy functions for backwards compatibility
def create_horizontal_bar_chart(data, title, color_scheme, current_total):
    """Legacy function - redirects to create_bar_chart."""
    return create_bar_chart(
        data=data,
        title=title,
        orientation='h',
        color_scheme=color_scheme,
        percentage_total=current_total
    )


def create_donut_chart(data, title):
    """Legacy function - redirects to create_pie_chart."""
    return create_pie_chart(
        data=data,
        title=title,
        hole=ChartConfig.DONUT_HOLE_SIZE
    )


def create_top_accounts_chart(top_accounts):
    """Legacy function for top accounts chart."""
    data = pd.Series(
        top_accounts['amount'].values,
        index=top_accounts['account'].values
    )
    
    fig = create_bar_chart(
        data=data,
        orientation='h',
        color_scheme='neutral'
    )
    
    # Add category to hover
    fig.update_traces(
        customdata=top_accounts['category'].values,
        hovertemplate='<b>%{y}</b><br>amount: $%{x:,.0f}<br>category: %{customdata}<extra></extra>'
    )
    
    return fig