"""Application-wide constants to eliminate magic strings."""


class TransactionTypes:
    """Transaction type identifiers."""
    INCOME = 'Income'
    EXPENSE = 'Expense'


class AccountTypes:
    """account_type identifiers."""
    LIABILITY = 'Liability'
    ASSET = 'Asset'


class ColumnNames:
    """Standard column names used across the application."""
    DATE = 'date'
    MONTH = 'month'
    MONTH_STR = 'month_Str'
    AMOUNT = 'amount'
    CATEGORY = 'category'
    SUBCATEGORY = 'subcategory'
    MERCHANT = 'merchant'
    ACCOUNT = 'account'
    ACCOUNT_TYPE = 'account_type'


class ComparisonTypes:
    """Comparison period types."""
    MONTH = 'Month'
    QUARTER = 'Quarter'
    YEAR = 'Year'


class ChartTypes:
    """Chart type identifiers."""
    BAR = 'bar'
    PIE = 'pie'
    LINE = 'line'
    STACKED_BAR = 'stacked_bar'
    DONUT = 'donut'


class FilterDefaults:
    """Default values for filters."""
    ALL = 'All'