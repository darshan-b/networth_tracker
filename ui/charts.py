"""Centralized chart creation with consistent styling."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List, Dict, Any
from config import ChartConfig, ColorSchemes
import plotly.io as pio
pio.templates.default = ChartConfig.TEMPLATE
from app_constants import ColumnNames
import yfinance as yf

PAYOUT_CHART_COLORS = {
    "forest": "#0B6B4B",
    "teal": "#2D8C74",
    "sage": "#A9D5C3",
    "sand": "#F6F1E8",
    "stone": "#6B7280",
    "ink": "#14213D",
    "line": "#D7E6DE",
    "principal": "#87C8B3",
    "contribution": "#D8EDE4",
    "return": "#0B6B4B",
    "warning": "#B45309",
    "danger": "#C2410C",
}


def _format_bar_value_label(value: float) -> str:
    """Format bar labels compactly so they fit cleanly above/outside bars."""
    abs_value = abs(value)

    if abs_value >= 1_000_000_000:
        formatted = f"${value / 1_000_000_000:.1f}B"
    elif abs_value >= 1_000_000:
        formatted = f"${value / 1_000_000:.1f}M"
    elif abs_value >= 1_000:
        formatted = f"${value / 1_000:.0f}K"
    else:
        formatted = f"${value:,.0f}"

    return formatted.replace(".0B", "B").replace(".0M", "M")


def _add_bar_axis_headroom(fig: go.Figure, data: pd.Series, orientation: str) -> None:
    """Extend the value axis so outside bar labels are not clipped."""
    if data.empty:
        return

    max_positive = max(float(data.max()), 0.0)
    min_negative = min(float(data.min()), 0.0)

    if max_positive == 0 and min_negative == 0:
        return

    positive_padding = max_positive * 0.14 if max_positive else 0.0
    negative_padding = abs(min_negative) * 0.14 if min_negative else 0.0

    axis_range = [min_negative - negative_padding, max_positive + positive_padding]

    if orientation == 'h':
        fig.update_xaxes(range=axis_range)
    else:
        fig.update_yaxes(range=axis_range)


def _apply_hover_style(fig: go.Figure) -> None:
    """Apply a shared hover-card style so charts feel more product-like."""
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor="rgba(15, 23, 42, 0.10)",
            font=dict(
                family=ChartConfig.FONT["family"],
                size=13,
                color="#0f172a",
            ),
        )
    )


def _apply_axis_style(fig: go.Figure, orientation: str = "v") -> None:
    """Soften gridlines, reduce visual noise, and add a little more breathing room."""
    if orientation == "h":
        fig.update_xaxes(
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.14)",
            gridwidth=1,
            zeroline=False,
            nticks=5,
        )
        fig.update_yaxes(showgrid=False, zeroline=False)
    else:
        fig.update_xaxes(showgrid=False, zeroline=False)
        fig.update_yaxes(
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.14)",
            gridwidth=1,
            zeroline=False,
            nticks=5,
        )

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
        color_scheme: Color scheme name ('assets', 'liabilities', 'neutral', 'categorical', 'networth')
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
        trace_config['text'] = [_format_bar_value_label(val) for val in data.values]
        trace_config['textposition'] = 'outside'
        trace_config['textfont'] = dict(size=11)
        trace_config['cliponaxis'] = False
    
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
        'margin': kwargs.get('margin', {'l': 36, 'r': 24, 't': 60, 'b': 42}),
        **axis_titles
    }
    
    if title:
        layout_config['title'] = title
    
    fig.update_layout(**layout_config)
    fig.update_traces(marker_line_width=0, marker_line_color="rgba(0,0,0,0)")
    fig.update_traces(marker=dict(cornerradius=10))
    _apply_hover_style(fig)
    _apply_axis_style(fig, orientation)

    if show_values:
        _add_bar_axis_headroom(fig, data, orientation)
    
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
        textposition='inside',
        textinfo='percent',
        hovertemplate='<b>%{label}</b><br>Amount: $%{value:,.0f}<br>As Percent: %{percent}',
        insidetextorientation='radial'
    ))
    
    layout_config = {
        'height': kwargs.get('height', ChartConfig.HEIGHT),
        'template': ChartConfig.TEMPLATE,
        'font': ChartConfig.FONT,
        'showlegend': show_legend,
        'margin': kwargs.get('margin', {'l': 28, 'r': 28, 't': 56, 'b': 36})
    }
    
    if show_legend:
        layout_config['legend'] = dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1
        )
    
    if title:
        layout_config['title'] = title
    
    fig.update_layout(**layout_config, uniformtext_minsize=16, uniformtext_mode='hide')
    _apply_hover_style(fig)
    
    return fig


def create_line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    color: Optional[str] = None,
    title: Optional[str] = None,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None,
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
        x_title: X-axis title (defaults to column name if None)
        y_title: Y-axis title (defaults to column name if None)
        markers: Whether to show markers on the line
        **kwargs: Additional arguments (height, line_width, marker_size)
       
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
        font=ChartConfig.FONT,
        hovermode=ChartConfig.HOVER_MODE,
        margin=kwargs.get('margin', {'l': 36, 'r': 24, 't': 60, 'b': 42}),
        xaxis_title=x_title if x_title else x,
        yaxis_title=y_title if y_title else y
    )
    
    fig.update_traces(
        line_width=kwargs.get('line_width', ChartConfig.LINE_WIDTH),
        marker=dict(size=kwargs.get('marker_size', ChartConfig.MARKER_SIZE))
    )
    _apply_hover_style(fig)
    _apply_axis_style(fig, "v")
    
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
        margin=kwargs.get('margin', {'l': 36, 'r': 24, 't': 60, 'b': 42}),
        xaxis_title=kwargs.get('x_label', ''),
        yaxis_title=kwargs.get('y_label', 'amount ($)')
    )
    fig.update_traces(marker_line_width=0, marker_line_color="rgba(0,0,0,0)")
    fig.update_traces(marker=dict(cornerradius=10))
    _apply_hover_style(fig)
    _apply_axis_style(fig, "v")
    
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
        margin=kwargs.get('margin', {'l': 36, 'r': 24, 't': 60, 'b': 42}),
        xaxis_title=kwargs.get('x_label', ''),
        yaxis_title=kwargs.get('y_label', 'amount ($)'),
        title=title
    )
    fig.update_traces(marker_line_width=0, marker_line_color="rgba(0,0,0,0)")
    fig.update_traces(marker=dict(cornerradius=10))
    _apply_hover_style(fig)
    _apply_axis_style(fig, "v")
    
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
        'categorical': ColorSchemes.CATEGORICAL,
        'networth': ColorSchemes.NETWORTH,
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


def create_donut_chart(data, title, color_scheme='categorical'):
    """Legacy function - redirects to create_pie_chart."""
    return create_pie_chart(
        data=data,
        title=title,
        hole=ChartConfig.DONUT_HOLE_SIZE,
        color_scheme=color_scheme,
    )


def create_top_accounts_chart(top_accounts, color_scheme='neutral'):
    """Legacy function for top accounts chart."""
    data = pd.Series(
        top_accounts[ColumnNames.AMOUNT].values,
        index=top_accounts[ColumnNames.ACCOUNT].values
    )
    
    fig = create_bar_chart(
        data=data,
        orientation='h',
        color_scheme=color_scheme
    )
    
    # Add category to hover
    fig.update_traces(
        customdata=top_accounts[ColumnNames.CATEGORY].values,
        hovertemplate='<b>%{y}</b><br>amount: $%{x:,.0f}<br>category: %{customdata}<extra></extra>'
    )
    
    return fig


def _format_payout_currency(value: float) -> str:
    return f"${value:,.0f}"


def _format_payout_inr_crore(value: float) -> str:
    return f"₹{value / 10_000_000:,.2f} Cr"


def _apply_payout_chart_theme(fig: go.Figure, *, height: int, yaxis_title: str, xaxis_title: Optional[str] = None) -> None:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=16, b=20),
        paper_bgcolor=PAYOUT_CHART_COLORS["sand"],
        plot_bgcolor="#FCFAF6",
        font=dict(color=PAYOUT_CHART_COLORS["ink"], size=13),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
            title_text="",
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor=PAYOUT_CHART_COLORS["line"],
            font=dict(color=PAYOUT_CHART_COLORS["ink"]),
        ),
        yaxis=dict(
            title=yaxis_title,
            gridcolor=PAYOUT_CHART_COLORS["line"],
            zerolinecolor=PAYOUT_CHART_COLORS["line"],
            tickfont=dict(color=PAYOUT_CHART_COLORS["stone"]),
            title_font=dict(color=PAYOUT_CHART_COLORS["stone"]),
        ),
        xaxis=dict(
            title=xaxis_title,
            tickfont=dict(color=PAYOUT_CHART_COLORS["stone"]),
            title_font=dict(color=PAYOUT_CHART_COLORS["stone"]),
        ),
    )


def create_payout_total_outcome_chart(scenarios: List[Dict[str, Any]]) -> go.Figure:
    labels = [str(scenario["label"]) for scenario in scenarios]
    totals = [float(scenario["total_usd"]) for scenario in scenarios]
    colors = [PAYOUT_CHART_COLORS["sage"], PAYOUT_CHART_COLORS["forest"]]
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=totals,
                marker_color=colors[: len(labels)],
                text=[_format_payout_currency(value) for value in totals],
                textposition="outside",
                customdata=[
                    [_format_payout_inr_crore(float(scenario["total_inr"])), scenario["note"]]
                    for scenario in scenarios
                ],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Net payout: %{text}<br>"
                    "INR equivalent: %{customdata[0]}<br>"
                    "%{customdata[1]}<extra></extra>"
                ),
            )
        ]
    )
    _apply_payout_chart_theme(fig, height=380, yaxis_title="USD")
    fig.update_layout(showlegend=False)
    return fig


def create_payout_mix_chart(scenarios: List[Dict[str, Any]], hsa_payout: float, vacation_payout: float) -> go.Figure:
    labels = [str(scenario["label"]) for scenario in scenarios]
    fig = go.Figure()
    components = [
        ("Cash / liquid assets", "liquidation_total", PAYOUT_CHART_COLORS["sand"]),
        ("Taxable net", "taxable_net", "#BFDCCF"),
        ("Retirement net", "retirement_net", PAYOUT_CHART_COLORS["forest"]),
        ("HSA payout", hsa_payout, PAYOUT_CHART_COLORS["teal"]),
        ("Vacation payout", vacation_payout, "#C7DCCF"),
    ]
    for name, key_or_value, color in components:
        values = [float(key_or_value)] * len(labels) if isinstance(key_or_value, (int, float)) else [float(s[key_or_value]) for s in scenarios]
        fig.add_bar(x=labels, y=values, name=name, marker_color=color, hovertemplate=f"{name}: %{{y:$,.0f}}<extra></extra>")
    _apply_payout_chart_theme(fig, height=420, yaxis_title="USD")
    fig.update_layout(barmode="stack")
    return fig


def create_payout_tax_drag_chart(scenarios: List[Dict[str, Any]]) -> go.Figure:
    labels = [str(scenario["label"]) for scenario in scenarios]
    fig = go.Figure()
    taxes = [
        ("Taxable gain tax", "taxable_tax", "#D6C4A8"),
        ("Federal retirement tax", "retirement_federal_tax", PAYOUT_CHART_COLORS["warning"]),
        ("State tax", "retirement_state_tax", "#D97706"),
        ("Early withdrawal penalty", "retirement_penalty_tax", PAYOUT_CHART_COLORS["danger"]),
    ]
    for name, key, color in taxes:
        fig.add_bar(x=labels, y=[float(scenario[key]) for scenario in scenarios], name=name, marker_color=color, hovertemplate=f"{name}: %{{y:$,.0f}}<extra></extra>")
    _apply_payout_chart_theme(fig, height=420, yaxis_title="USD")
    fig.update_layout(barmode="stack")
    return fig


def create_payout_rnor_advantage_chart(withdraw_now: Dict[str, Any], new_year_rnor: Dict[str, Any]) -> go.Figure:
    taxable_savings = float(withdraw_now["taxable_tax"]) - float(new_year_rnor["taxable_tax"])
    federal_savings = float(withdraw_now["retirement_federal_tax"]) - float(new_year_rnor["retirement_federal_tax"])
    state_savings = float(withdraw_now["retirement_state_tax"]) - float(new_year_rnor["retirement_state_tax"])
    penalty_savings = float(withdraw_now["retirement_penalty_tax"]) - float(new_year_rnor["retirement_penalty_tax"])
    fig = go.Figure(
        go.Waterfall(
            x=["Withdraw Now", "Taxable tax saved", "Federal tax saved", "State tax change", "Penalty change", "New Year RNOR"],
            measure=["absolute", "relative", "relative", "relative", "relative", "absolute"],
            y=[
                float(withdraw_now["total_usd"]),
                taxable_savings,
                federal_savings,
                state_savings,
                penalty_savings,
                float(new_year_rnor["total_usd"]),
            ],
            connector={"line": {"color": "#7C746A"}},
            increasing={"marker": {"color": PAYOUT_CHART_COLORS["forest"]}},
            decreasing={"marker": {"color": PAYOUT_CHART_COLORS["danger"]}},
            totals={"marker": {"color": PAYOUT_CHART_COLORS["sage"]}},
            text=[
                _format_payout_currency(float(withdraw_now["total_usd"])),
                _format_payout_currency(taxable_savings),
                _format_payout_currency(federal_savings),
                _format_payout_currency(state_savings),
                _format_payout_currency(penalty_savings),
                _format_payout_currency(float(new_year_rnor["total_usd"])),
            ],
            textposition="outside",
            hovertemplate="%{x}: %{text}<extra></extra>",
        )
    )
    _apply_payout_chart_theme(fig, height=420, yaxis_title="USD")
    fig.update_layout(showlegend=False)
    return fig


def create_payout_rnor_projection_chart(projection_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=projection_df["Year"], y=projection_df["Principal Crores"], name="Invested principal", marker_color=PAYOUT_CHART_COLORS["principal"], marker_line_color="#78B5A1", marker_line_width=1, hovertemplate="Year %{x}<br>Principal: ₹%{y:.2f} Cr<extra></extra>"))
    fig.add_trace(go.Bar(x=projection_df["Year"], y=projection_df["Contributions Crores"], name="Monthly contributions", marker_color=PAYOUT_CHART_COLORS["contribution"], marker_line_color="#BDD9CC", marker_line_width=1, hovertemplate="Year %{x}<br>Contributions: ₹%{y:.2f} Cr<extra></extra>"))
    fig.add_trace(go.Bar(x=projection_df["Year"], y=projection_df["Return Crores"], name="Accumulated return", marker_color=PAYOUT_CHART_COLORS["return"], marker_line_color="#09553B", marker_line_width=1, hovertemplate="Year %{x}<br>Return: ₹%{y:.2f} Cr<extra></extra>"))
    _apply_payout_chart_theme(fig, height=440, yaxis_title="INR (Crores)", xaxis_title="Years After Withdrawal")
    fig.update_layout(barmode="stack", bargap=0.18)
    return fig

def create_portfolio_value_chart(df, date_col='Date', value_col='Current Value'):
    """Create portfolio value over time chart."""
    fig = go.Figure()
    
    df_sorted = df.sort_values(date_col)
    
    fig.add_trace(go.Scatter(
        x=df_sorted[date_col],
        y=df_sorted[value_col],
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))
    
    fig.update_layout(
        title='Portfolio Value Over Time',
        xaxis_title='Date',
        yaxis_title='Value ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_allocation_chart(latest_df):
    """Create asset allocation pie chart from historical data."""
    allocation = latest_df[latest_df['Current Value'] > 0].copy()
    allocation = allocation.sort_values('Current Value', ascending=False)
    label_column = 'Position' if 'Position' in allocation.columns else 'ticker'
    
    fig = px.pie(
        allocation,
        values='Current Value',
        names=label_column,
        title='Asset Allocation by Current Value',
        hole=0.4
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_gain_loss_chart(latest_df):
    """Create gain/loss bar chart by symbol from historical data."""
    data = latest_df[latest_df['quantity'] > 0].copy()
    data = data.sort_values('Total Gain/Loss')
    label_column = 'Position' if 'Position' in data.columns else 'ticker'
    
    colors = ['red' if x < 0 else 'green' for x in data['Total Gain/Loss']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=data[label_column],
        y=data['Total Gain/Loss'],
        marker_color=colors,
        text=data['Total Gain/Loss'].apply(lambda x: f'${x:,.2f}'),
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Gain/Loss by Symbol',
        xaxis_title=label_column,
        yaxis_title='Gain/Loss ($)',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_performance_comparison(df, symbols):
    """Create normalized performance comparison chart."""
    fig = go.Figure()
    
    for symbol in symbols:
        symbol_data = (
            df[df['ticker'] == symbol]
            .groupby('Date', as_index=False)['Last Close']
            .mean()
            .sort_values('Date')
        )
        if len(symbol_data) > 0:
            normalized = (symbol_data['Last Close'] / symbol_data['Last Close'].iloc[0]) * 100
            
            fig.add_trace(go.Scatter(
                x=symbol_data['Date'],
                y=normalized,
                mode='lines',
                name=symbol
            ))
    
    fig.update_layout(
        title='Normalized Performance Comparison (Base 100)',
        xaxis_title='Date',
        yaxis_title='Normalized Value',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_correlation_heatmap(df):
    """Create correlation heatmap for portfolio symbols."""
    deduped = (
        df.groupby(['Date', 'ticker'], as_index=False)['Last Close']
        .mean()
    )
    price_pivot = deduped.pivot_table(
        index='Date',
        columns='ticker',
        values='Last Close'
    )
    
    returns = price_pivot.pct_change().dropna()
    correlation = returns.corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=correlation.values,
        x=correlation.columns,
        y=correlation.index,
        colorscale='RdBu',
        zmid=0,
        text=correlation.values.round(2),
        texttemplate='%{text}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation")
    ))
    
    fig.update_layout(
        title='Asset Correlation Matrix',
        height=500,
        template='plotly_white'
    )
    
    return fig

def create_drawdown_chart(df, date_col='Date', value_col='Current Value'):
    """Create drawdown chart."""
    df = df.sort_values(date_col)
    cumulative = df[value_col] / df[value_col].iloc[0]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df[date_col],
        y=drawdown,
        mode='lines',
        name='Drawdown',
        fill='tozeroy',
        line=dict(color='red')
    ))
    
    fig.update_layout(
        title='Portfolio Drawdown',
        xaxis_title='Date',
        yaxis_title='Drawdown (%)',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_transaction_timeline(trading_log_df):
    """Create transaction timeline."""
    fig = go.Figure()
    
    for trans_type in trading_log_df['Transaction Type'].unique():
        df_type = trading_log_df[trading_log_df['Transaction Type'] == trans_type]
        
        fig.add_trace(go.Scatter(
            x=df_type['Date'],
            y=df_type['Amount'],
            mode='markers',
            name=trans_type,
            marker=dict(size=10),
            text=df_type['ticker'],
            hovertemplate='<b>%{text}</b><br>Date: %{x}<br>Amount: $%{y:,.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        title='Transaction Timeline',
        xaxis_title='Date',
        yaxis_title='Amount ($)',
        hovermode='closest',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_cost_basis_comparison(historical_df):
    """Create cost basis vs current value vs S&P 500 comparison chart.
    S&P 500 shows what portfolio would be worth if same investments were made in S&P 500."""
    
    daily_totals = historical_df.groupby('Date').agg({
        'Current Value': 'sum',
        'Cost Basis': 'sum'
    }).reset_index().sort_values('Date')
    
    if daily_totals.empty or len(daily_totals) < 2:
        return None
    
    fig = go.Figure()
    
    # Add Cost Basis
    fig.add_trace(go.Scatter(
        x=daily_totals['Date'],
        y=daily_totals['Cost Basis'],
        mode='lines',
        name='Cost Basis (Total Invested)',
        line=dict(color='orange', dash='dash', width=2)
    ))
    
    # Add Current Value
    fig.add_trace(go.Scatter(
        x=daily_totals['Date'],
        y=daily_totals['Current Value'],
        mode='lines',
        name='Portfolio Value',
        line=dict(color='green', width=2)
    ))
    
    # Calculate S&P 500 equivalent investment
    start_date = daily_totals['Date'].min()
    end_date = daily_totals['Date'].max()
    
    try:
        # Fetch S&P 500 historical data
        sp500 = yf.Ticker("^GSPC")
        sp500_hist = sp500.history(start=start_date, end=end_date)
        
        if not sp500_hist.empty:
            # Prepare S&P 500 price data
            sp500_prices = pd.DataFrame({
                'Date': pd.to_datetime(sp500_hist.index).tz_localize(None),
                'Close': sp500_hist['Close'].values
            })
            
            # Calculate cost basis changes (new investments)
            daily_totals['Cost_Change'] = daily_totals['Cost Basis'].diff().fillna(daily_totals['Cost Basis'])
            
            # Simulate S&P 500 investment
            sp500_shares = 0
            sp500_values = []
            
            for _, row in daily_totals.iterrows():
                date = row['Date']
                cost_change = row['Cost_Change']
                
                # Get S&P 500 price for this date
                sp500_price_row = sp500_prices[sp500_prices['Date'] == date]
                
                if not sp500_price_row.empty:
                    sp500_price = sp500_price_row['Close'].iloc[0]
                    
                    # If new money was invested, buy S&P 500 shares
                    if cost_change > 0:
                        sp500_shares += cost_change / sp500_price
                    
                    # Calculate current S&P 500 portfolio value
                    sp500_value = sp500_shares * sp500_price
                    sp500_values.append({'Date': date, 'Value': sp500_value})
            
            if sp500_values:
                sp500_df = pd.DataFrame(sp500_values)
                
                fig.add_trace(go.Scatter(
                    x=sp500_df['Date'],
                    y=sp500_df['Value'],
                    mode='lines',
                    name='S&P 500 (If Invested Same Amounts)',
                    line=dict(color='blue', width=2, dash='dot')
                ))
    except Exception as e:
        print(f"Error calculating S&P 500 comparison: {e}")
    
    fig.update_layout(
        title='Portfolio Performance vs Cost Basis vs S&P 500',
        xaxis_title='Date',
        yaxis_title='Value ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    return fig
