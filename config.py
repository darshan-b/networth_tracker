"""Configuration and constants for Net Worth Tracker."""

COLORS = {
    'primary': '#1f77b4',
    'success': '#2ca02c',
    'warning': '#ff7f0e',
    'danger': '#d62728',
    'info': '#17becf',
    'purple': '#9467bd',
    'assets': ['#d4edda', '#c3e6cb', '#b1dfbb', '#a0d8ab', '#8fd19e', '#7eca91'],
    'liabilities': ['#f8d7da', '#f5c6cb', '#f1b0b7', '#ee9ca4', '#eb8891', '#e8737e'],
    'neutral': ['#e8f4f8', '#d1e7f0', '#b8dae8', '#a0cde0', '#87c0d8', '#6fb3d0']
}

CHART_CONFIG = {
    'height': 320,
    'margin': dict(l=20, r=20, t=30, b=20),
    'template': 'plotly_white',
    'font': dict(size=12, family='Arial, sans-serif')
}

HOVER_TEMPLATE = '<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
BAR_HOVER_TEMPLATE = '<b>%{y}</b><br>Amount: $%{x:,.0f}<br>%{customdata}<extra></extra>'