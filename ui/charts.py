"""Chart creation functions."""

import plotly.graph_objects as go
from config import COLORS, CHART_CONFIG


def create_horizontal_bar_chart(data, title, color_scheme, current_total):
    """Create a horizontal bar chart for category breakdown.
    
    Args:
        data: Series with category names as index and amounts as values
        title: Chart title
        color_scheme: Color scheme name ('assets', 'liabilities', or 'neutral')
        current_total: Total amount for percentage calculation
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    colors = COLORS.get(color_scheme, COLORS['neutral'])
    
    fig.add_trace(go.Bar(
        x=data.values,
        y=data.index,
        orientation='h',
        marker=dict(
            color=colors[:len(data)],
            line=dict(color='rgba(0,0,0,0.1)', width=1)
        ),
        text=[f'${val:,.0f}' for val in data.values],
        textposition='outside',
        textfont=dict(size=11),
        hovertemplate='<b>%{y}</b><br>Amount: $%{x:,.0f}<br>Share: %{customdata:.1f}%<extra></extra>',
        customdata=[val/current_total*100 if current_total > 0 else 0 for val in data.values]
    ))
    
    fig.update_layout(
        height=CHART_CONFIG['height'],
        template=CHART_CONFIG['template'],
        font=CHART_CONFIG['font'],
        xaxis_title='Amount ($)',
        yaxis_title='',
        showlegend=False,
        margin=CHART_CONFIG['margin']
    )
    
    return fig


def create_donut_chart(data, title):
    """Create a donut/pie chart.
    
    Args:
        data: Series with labels as index and values
        title: Chart title
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=data.index,
        values=data.values,
        hole=0.4,
        marker=dict(
            colors=[COLORS['success'], COLORS['warning'], COLORS['primary'], COLORS['danger']][:len(data)],
            line=dict(color='white', width=2)
        ),
        textposition='auto',
        textinfo='label+percent',
        textfont=dict(size=11),
        hovertemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
    ))
    
    fig.update_layout(
        height=CHART_CONFIG['height'],
        template=CHART_CONFIG['template'],
        font=CHART_CONFIG['font'],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=CHART_CONFIG['margin']
    )
    
    return fig


def create_top_accounts_chart(top_accounts):
    """Create horizontal bar chart for top accounts.
    
    Args:
        top_accounts: DataFrame with Account, Amount, Category columns
        
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=top_accounts['Amount'],
        y=top_accounts['Account'],
        orientation='h',
        marker=dict(
            color=COLORS['neutral'][:len(top_accounts)],
            line=dict(color='rgba(0,0,0,0.1)', width=1)
        ),
        text=[f'${val:,.0f}' for val in top_accounts['Amount']],
        textposition='outside',
        textfont=dict(size=11),
        hovertemplate='<b>%{y}</b><br>Amount: $%{x:,.0f}<br>Category: %{customdata}<extra></extra>',
        customdata=top_accounts['Category']
    ))
    
    fig.update_layout(
        height=CHART_CONFIG['height'],
        template=CHART_CONFIG['template'],
        font=CHART_CONFIG['font'],
        xaxis_title='Amount ($)',
        yaxis_title='',
        showlegend=False,
        margin=CHART_CONFIG['margin']
    )
    
    return fig
