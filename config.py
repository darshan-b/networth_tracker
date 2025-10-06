"""Application-wide configuration settings."""

import plotly.express as px
from constants import ColumnNames


class ChartConfig:
    """Chart styling and layout configuration."""
    
    # Default dimensions
    HEIGHT = None
    WIDTH = None  # None = responsive width
    
    # Plotly template
    TEMPLATE = 'plotly_dark'
    
    # Font settings
    FONT = {
        'family': 'Arial, sans-serif',
        'size': 12,
        'color': 'black'
    }
    
    # Margins
    MARGIN = {
        'l': 50,
        'r': 50,
        't': 50,
        'b': 50
    }
    
    # Chart-specific settings
    BAR_LINE_WIDTH = 1
    BAR_LINE_COLOR = 'rgba(0,0,0,0.1)'
    DONUT_HOLE_SIZE = 0.55
    LINE_WIDTH = 3
    MARKER_SIZE = 8
    
    # Hover settings
    HOVER_MODE = 'x unified'


class ColorSchemes:
    """Color palettes for different chart types."""
    
    # Asset colors (greens)
    ASSETS = [
        '#4CAF50',  # Green
        '#8BC34A',  # Light Green
        '#CDDC39',  # Lime
        '#66BB6A',  # Medium Green
        '#AED581'   # Pale Green
    ]
    
    # Liability colors (reds)
    LIABILITIES = [
        '#F44336',  # Red
        '#E91E63',  # Pink
        '#9C27B0',  # Purple
        '#EF5350',  # Light Red
        '#EC407A'   # Medium Pink
    ]
    
    # Neutral colors (grays/blues)
    NEUTRAL = [
        '#607D8B',  # Blue Gray
        '#90A4AE',  # Light Blue Gray
        '#78909C',  # Medium Blue Gray
        '#B0BEC5',  # Pale Blue Gray
        '#CFD8DC'   # Very Light Blue Gray
    ]
    
    # Categorical colors (for categories)
    CATEGORICAL = px.colors.qualitative.Dark2
    
    # Status colors
    SUCCESS = '#4CAF50'
    WARNING = '#FF9800'
    DANGER = '#F44336'
    PRIMARY = '#2196F3'
    INFO = '#00BCD4'
    
    # Gradient colors for continuous scales
    GRADIENT_GREEN = 'Greens'
    GRADIENT_RED = 'Reds'
    GRADIENT_BLUE = 'Blues'
    GRADIENT_PURPLE = 'Purples'


class UIConfig:
    """UI component configuration."""
    
    # Default column counts
    METRIC_COLUMNS = 3
    FILTER_COLUMNS = 3
    CHART_COLUMNS = 2
    
    # Date format
    DATE_FORMAT = '%b %Y'
    DATE_FORMAT_FULL = '%B %d, %Y'
    
    # Number formatting
    CURRENCY_FORMAT = '${:,.0f}'
    CURRENCY_FORMAT_DETAILED = '${:,.2f}'
    PERCENT_FORMAT = '{:.1f}%'
    PERCENT_FORMAT_DETAILED = '{:.2f}%'
    
    # Table settings
    TABLE_PAGE_SIZE = 50
    TABLE_HEIGHT = 400
    
    # Chart settings
    CHART_USE_CONTAINER_WIDTH = True
    
    # Progress bar thresholds
    BUDGET_WARNING_THRESHOLD = 80  # Percent
    BUDGET_DANGER_THRESHOLD = 100  # Percent


class AnalysisConfig:
    """Configuration for analysis and calculations."""
    
    # Default analysis periods
    DEFAULT_MONTHS = 12
    DEFAULT_QUARTERS = 4
    DEFAULT_YEARS = 3
    
    # Top N settings
    TOP_MERCHANTS_LIMIT = 10
    TOP_CATEGORIES_LIMIT = 5
    TOP_ACCOUNTS_LIMIT = 5
    
    # Projection settings
    DEFAULT_ANNUAL_RETURN = 7.0  # Percent
    DEFAULT_MONTHLY_CONTRIBUTION = 1000
    MAX_PROJECTION_MONTHS = 600  # 50 years
    
    # Growth calculation
    ROLLING_WINDOW_SIZE = 3  # For moving averages
    MILESTONE_VALUES = [100000, 250000, 500000, 750000, 1000000, 1500000, 2000000]


class DataConfig:
    """Data processing configuration."""
    
    # Required columns for different views
    EXPENSE_REQUIRED_COLUMNS = [ColumnNames.DATE, ColumnNames.AMOUNT, ColumnNames.CATEGORY, ColumnNames.MERCHANT, ColumnNames.ACCOUNT]
    NETWORTH_REQUIRED_COLUMNS = [ColumnNames.MONTH, ColumnNames.AMOUNT, 'account_type', ColumnNames.CATEGORY]
    
    # Column type mappings
    NUMERIC_COLUMNS = [ColumnNames.AMOUNT, ColumnNames.AMOUNT]
    DATE_COLUMNS = [ColumnNames.DATE, ColumnNames.MONTH]
    
    # Data validation
    MIN_ROWS_FOR_ANALYSIS = 2
    MIN_PERIODS_FOR_TRENDS = 3


# Legacy support - map old config to new structure
COLORS = {
    'assets': ColorSchemes.ASSETS,
    'liabilities': ColorSchemes.LIABILITIES,
    'neutral': ColorSchemes.NEUTRAL,
    'success': ColorSchemes.SUCCESS,
    'warning': ColorSchemes.WARNING,
    'danger': ColorSchemes.DANGER,
    'primary': ColorSchemes.PRIMARY
}

CHART_CONFIG = {
    'height': ChartConfig.HEIGHT,
    'template': ChartConfig.TEMPLATE,
    'font': ChartConfig.FONT,
    'margin': ChartConfig.MARGIN
}