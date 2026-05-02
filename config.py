"""Application-wide configuration settings."""

import plotly.express as px
from app_constants import ColumnNames


class ChartConfig:
    """Chart styling and layout configuration."""
    
    # Default dimensions
    HEIGHT = None
    WIDTH = None  # None = responsive width
    
    # Plotly template
    TEMPLATE = 'plotly_white'
    
    # Font settings
    FONT = {
        'family': 'Aptos, Segoe UI, sans-serif',
        'size': 12,
        'color': '#1f2937'
    }
    
    # Margins
    MARGIN = {
        'l': 32,
        'r': 24,
        't': 48,
        'b': 32
    }
    
    # Chart-specific settings
    BAR_LINE_WIDTH = 1
    BAR_LINE_COLOR = 'rgba(0,0,0,0.1)'
    DONUT_HOLE_SIZE = 0.55
    LINE_WIDTH = 3
    MARKER_SIZE = 8
    
    # Hover settings
    HOVER_MODE = 'x unified'
    
    # Streamlit chart rendering config
    STREAMLIT_CONFIG = {
        'responsive': True
    }


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
    
    # Categorical colors (shared across overview/comparison charts)
    CATEGORICAL = [
        '#0F766E',
        '#3B82F6',
        '#94A3B8',
        '#F59E0B',
        '#EF4444',
        '#8B5CF6',
        '#14B8A6',
        '#64748B',
    ]

    # Net worth palette: softer, cohesive tones for subtype/type/institution breakdowns
    NETWORTH = [
        '#c7522a',
        '#e5c185',
        '#f0daa5',
        '#fbf2c4',
        '#b8cdab',
        '#74a892',
        '#008585',
        '#004343',
    ]
    
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
    CHART_RENDER_CONFIG = ChartConfig.STREAMLIT_CONFIG
    
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
    NETWORTH_REQUIRED_COLUMNS = [ColumnNames.MONTH, ColumnNames.AMOUNT, ColumnNames.ACCOUNT_TYPE, ColumnNames.CATEGORY]
    
    # Column type mappings
    NUMERIC_COLUMNS = [ColumnNames.AMOUNT, ColumnNames.AMOUNT]
    DATE_COLUMNS = [ColumnNames.DATE, ColumnNames.MONTH]
    
    # Data validation
    MIN_ROWS_FOR_ANALYSIS = 2
    MIN_PERIODS_FOR_TRENDS = 3


class AppConfig:
    """Top-level application text and layout configuration."""

    TITLE = "Personal Finance Tracker"
    PAGE_ICON = "/data/raw/cash-flow.png"
    LAYOUT = "wide"
    NAVIGATION_TITLE = "Navigation"
    VIEW_SELECTOR_LABEL = "Select View"
    GETTING_STARTED_TITLE = "Getting Started"
    GETTING_STARTED_STEPS = [
        "Add your local data files under `data/raw/`.",
        "Launch the app with `streamlit run app.py`.",
        "If a page is empty, check the expected file names and columns in `README.md`."
    ]
    VIEW_OPTIONS = [
        "Net Worth Tracker",
        "Expense Tracker",
        "Stock Tracker",
    ]
    VIEW_HELP = "Choose between Net Worth tracking, Expense tracking, or Stock portfolio analysis"


class StockTrackerConfig:
    """Stock tracker labels and visible copy."""

    TITLE = "Portfolio Analysis Dashboard"
    FILTER_SUMMARY_TITLE = "Active Filters"
    FILTER_DATE_RANGE_LABEL = "Date Range"
    FILTER_DATE_RANGE_ALL = "Date Range: All"
    AVAILABLE_COLUMNS_TITLE = "Available columns in your data"
    ERROR_DETAILS_TITLE = "Error Details"
    TAB_NAMES = [
        "Overview",
        "Performance",
        "Allocation",
        "Risk Analysis",
        "Transactions",
        "Cost Basis",
    ]


class NetWorthConfig:
    """Net worth feature labels and shared options."""

    TAB_NAMES = [
        "Overview",
        "Net Worth Over Time",
        "Payout",
        "Summarized Table",
        "Growth Projections",
        "Data Explorer"
    ]
    PIVOT_TITLE = "Summarized Table"
    PIVOT_DOWNLOAD_LABEL = "Download Pivot Table (Excel)"
    PIVOT_DOWNLOAD_FILENAME = "pivot_table.xlsx"
    COMPARISON_OPTIONS = ["Monthly", "Quarterly", "Yearly"]
    COMPARISON_LABELS = {
        "Monthly": "MoM",
        "Quarterly": "QoQ",
        "Yearly": "YoY",
    }
    PERIOD_LABELS = {
        "Monthly": "Monthly",
        "Quarterly": "Quarterly",
        "Yearly": "Yearly",
    }
    KPI_CURRENT_NET_WORTH = "Current Net Worth"
    KPI_TOTAL_CHANGE = "Total Change"
    KPI_STARTING_NET_WORTH = "Starting Net Worth"
    KPI_KEY_METRICS_TITLE = "### Key Metrics"


class NetWorthOverviewConfig:
    """Shared visual config for the Net Worth overview tab."""

    PANEL_STYLES = {
        "assets": {
            "accent": ColorSchemes.ASSETS[0],
            "border": "rgba(15, 118, 110, 0.12)",
            "background": "linear-gradient(180deg, #f5fbf7 0%, #edf8f2 100%)",
        },
        "liabilities": {
            "accent": ColorSchemes.LIABILITIES[0],
            "border": "rgba(185, 28, 28, 0.12)",
            "background": "linear-gradient(180deg, #fff7f7 0%, #fff0f0 100%)",
        },
        "neutral": {
            "accent": ColorSchemes.NEUTRAL[0],
            "border": "rgba(96, 125, 139, 0.12)",
            "background": "linear-gradient(180deg, #f8fafc 0%, #f2f6f9 100%)",
        },
    }


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
