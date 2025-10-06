"""Financial calculations and metrics.

This module provides financial calculation utilities for analyzing account data,
expenses, budgets, and trends.
"""

from typing import Dict, List, Optional, Any

import pandas as pd
import streamlit as st

from constants import AccountTypes, ColumnNames
from config import AnalysisConfig


# Trend indicators
TREND_UP = "↑"
TREND_DOWN = "↓"
TREND_FLAT = "→"

# Days of week in order
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


class FinancialCalculationError(Exception):
    """Custom exception for financial calculation errors."""
    pass


def _validate_dataframe(df: pd.DataFrame, required_columns: List[str], name: str = "DataFrame") -> None:
    """Validate that a DataFrame contains required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of column names that must be present
        name: Name of the DataFrame for error messages
        
    Raises:
        FinancialCalculationError: If DataFrame is invalid or missing columns
    """
    if df is None:
        raise FinancialCalculationError(f"{name} cannot be None")
    
    if not isinstance(df, pd.DataFrame):
        raise FinancialCalculationError(f"{name} must be a pandas DataFrame")
    
    if df.empty:
        st.warning(f"{name} is empty")
    
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise FinancialCalculationError(
            f"{name} missing required columns: {', '.join(missing_cols)}"
        )


def _convert_to_absolute(amount: float) -> float:
    """Convert amount to absolute value for display purposes.
    
    Args:
        amount: The amount to convert
        
    Returns:
        Absolute value of the amount
    """
    return abs(amount)


def calculate_account_info(
    data: pd.DataFrame, 
    accounts: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Calculate current values and trends for each account.
    
    Args:
        data: Full dataset with columns [ColumnNames.ACCOUNT, ColumnNames.MONTH, ColumnNames.AMOUNT, 'account_type']
        accounts: List of account names to analyze
        
    Returns:
        Dictionary mapping account names to info dictionaries containing:
            - value: Current account value
            - change: Change from previous period
            - trend: Trend indicator (↑, ↓, or →)
            - type: account_type
            
    Raises:
        FinancialCalculationError: If data is invalid or missing required columns
    """
    required_cols = [
        ColumnNames.ACCOUNT,
        ColumnNames.MONTH,
        ColumnNames.AMOUNT,
        ColumnNames.ACCOUNT_TYPE
    ]
    _validate_dataframe(data, required_cols, "data")
    
    if not accounts:
        st.warning("No accounts provided for calculation")
        return {}
    
    account_info = {}
    
    for account in accounts:
        try:
            acct_data = data[data[ColumnNames.ACCOUNT] == account].sort_values(ColumnNames.MONTH)
            
            if acct_data.empty:
                continue
            
            if len(acct_data) >= 2:
                current_val = acct_data.iloc[-1][ColumnNames.AMOUNT]
                prev_val = acct_data.iloc[-2][ColumnNames.AMOUNT]
                change = current_val - prev_val
                
                if change > 0:
                    trend = TREND_UP
                elif change < 0:
                    trend = TREND_DOWN
                else:
                    trend = TREND_FLAT
            elif len(acct_data) == 1:
                current_val = acct_data.iloc[-1][ColumnNames.AMOUNT]
                change = 0
                trend = TREND_FLAT
            else:
                continue
            
            account_info[account] = {
                'value': current_val,
                'change': change,
                'trend': trend,
                'type': acct_data.iloc[-1][ColumnNames.ACCOUNT_TYPE]
            }
            
        except Exception as e:
            st.error(f"Error calculating info for account {account}: {str(e)}")
            continue
    
    return account_info


def calculate_metrics(
    latest_data: pd.DataFrame, 
    previous_data: Optional[pd.DataFrame] = None
) -> Dict[str, float]:
    """Calculate key financial networth account metrics.
    
    Args:
        latest_data: DataFrame for current month with columns ['Account Type', 'Amount']
        previous_data: DataFrame for previous month (optional)
        
    Returns:
        Dictionary containing:
            - current_assets: Total assets for current period
            - current_liabilities: Total liabilities (positive value)
            - current_net_worth: Net worth (assets - liabilities)
            - net_worth_change: Change in net worth from previous period
            - net_worth_pct_change: Percentage change in net worth
            - liabilities_change: Change in liabilities
            - liabilities_change_pct: Percentage change in liabilities
            - debt_ratio: Debt to assets ratio
            
    Raises:
        FinancialCalculationError: If data is invalid or missing required columns
    """
    required_cols = [ColumnNames.ACCOUNT_TYPE, ColumnNames.AMOUNT]
    _validate_dataframe(latest_data, required_cols, "latest_data")
    
    # Current period calculations
    current_assets = latest_data[
        latest_data[ColumnNames.ACCOUNT_TYPE] != AccountTypes.LIABILITY
    ][ColumnNames.AMOUNT].sum()
    
    current_liabilities_raw = latest_data[
        latest_data[ColumnNames.ACCOUNT_TYPE] == AccountTypes.LIABILITY
    ][ColumnNames.AMOUNT].sum()
    
    current_liabilities = _convert_to_absolute(current_liabilities_raw)
    current_net_worth = current_assets + current_liabilities_raw
    
    # Calculate debt ratio
    total_assets_and_nw = current_net_worth + current_liabilities
    debt_ratio = (
        (current_liabilities / total_assets_and_nw * 100) 
        if total_assets_and_nw > 0 else 0.0
    )
    
    metrics = {
        'current_assets': current_assets,
        'current_liabilities': current_liabilities,
        'current_net_worth': current_net_worth,
        'net_worth_change': 0.0,
        'net_worth_pct_change': 0.0,
        'liabilities_change': 0.0,
        'liabilities_change_pct': 0.0,
        'debt_ratio': debt_ratio
    }
    
    # Previous period comparisons
    if previous_data is not None and not previous_data.empty:
        try:
            _validate_dataframe(previous_data, required_cols, "previous_data")
            
            prev_assets = previous_data[
                previous_data[ColumnNames.ACCOUNT_TYPE] != AccountTypes.LIABILITY
            ][ColumnNames.AMOUNT].sum()
            
            prev_liabilities_raw = previous_data[
                previous_data[ColumnNames.ACCOUNT_TYPE] == AccountTypes.LIABILITY
            ][ColumnNames.AMOUNT].sum()
            
            prev_liabilities = _convert_to_absolute(prev_liabilities_raw)
            prev_net_worth = prev_assets + prev_liabilities_raw
            
            # Calculate changes
            metrics['net_worth_change'] = current_net_worth - prev_net_worth
            metrics['net_worth_pct_change'] = (
                (metrics['net_worth_change'] / prev_net_worth * 100) 
                if prev_net_worth != 0 else 0.0
            )
            
            metrics['liabilities_change'] = current_liabilities - prev_liabilities
            metrics['liabilities_change_pct'] = (
                (metrics['liabilities_change'] / prev_liabilities * 100) 
                if prev_liabilities != 0 else 0.0
            )
            
        except Exception as e:
            st.warning(f"Could not calculate period-over-period metrics: {str(e)}")
    
    return metrics


def calculate_expense_summary(
    df: pd.DataFrame, 
    budgets: Dict[str, float], 
    num_months: int = 1
) -> Dict[str, float]:
    """Calculate summary statistics for expenses.
    
    Args:
        df: Transactions dataframe (already filtered for expenses) with column [ColumnNames.AMOUNT]
        budgets: Dictionary mapping category names to monthly budget amounts
        num_months: Number of distinct months in the selected range
        
    Returns:
        Dictionary containing:
            - total_spent: Total amount spent
            - total_budget: Total budget for the period
            - remaining: Budget remaining
            - num_transactions: Number of transactions
            - avg_transaction: Average transaction amount
            
    Raises:
        FinancialCalculationError: If data is invalid
    """
    _validate_dataframe(df, [ColumnNames.AMOUNT], "df")
    
    if not isinstance(budgets, dict):
        raise FinancialCalculationError("budgets must be a dictionary")
    
    if num_months < 1:
        raise FinancialCalculationError("num_months must be at least 1")
    
    # Use absolute values for expenses
    total_spent = _convert_to_absolute(df[ColumnNames.AMOUNT].sum())
    # scale budget with number of months selected
    total_budget = sum(budgets.values()) * num_months
    remaining = total_budget - total_spent
    num_transactions = len(df)
    
    avg_transaction = total_spent / num_transactions if num_transactions > 0 else 0.0
    
    return {
        'total_spent': total_spent,
        'total_budget': total_budget,
        'remaining': remaining,
        'num_transactions': num_transactions,
        'avg_transaction': avg_transaction
    }


def calculate_category_spending(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate spending by category.
    
    Args:
        df: Transactions dataframe with columns [ColumnNames.CATEGORY, ColumnNames.AMOUNT]
        
    Returns:
        DataFrame with columns [ColumnNames.CATEGORY, ColumnNames.AMOUNT] sorted by amount descending.
        amounts are converted to absolute values.
        
    Raises:
        FinancialCalculationError: If data is invalid
    """
    required_cols = [ColumnNames.CATEGORY, ColumnNames.AMOUNT]
    _validate_dataframe(df, required_cols, "df")
    
    category_spending = (
        df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .reset_index()
    )
    category_spending[ColumnNames.AMOUNT] = category_spending[ColumnNames.AMOUNT].apply(_convert_to_absolute)
    category_spending = category_spending.sort_values(ColumnNames.AMOUNT, ascending=False)
    category_spending = (
        category_spending.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
    )

    return category_spending


def calculate_account_spending(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate spending by account.
    
    Args:
        df: Transactions dataframe with columns [ColumnNames.ACCOUNT, ColumnNames.AMOUNT]
        
    Returns:
        DataFrame with columns [ColumnNames.ACCOUNT, ColumnNames.AMOUNT] sorted by amount descending.
        amounts are converted to absolute values.
        
    Raises:
        FinancialCalculationError: If data is invalid
    """
    required_cols = [ColumnNames.ACCOUNT, ColumnNames.AMOUNT]
    _validate_dataframe(df, required_cols, "df")
    
    account_spending = (
        df.groupby(ColumnNames.ACCOUNT)[ColumnNames.AMOUNT]
        .sum()
        .reset_index()
    )
    account_spending[ColumnNames.AMOUNT] = account_spending[ColumnNames.AMOUNT].apply(_convert_to_absolute)
    account_spending = account_spending.sort_values(ColumnNames.AMOUNT, ascending=False)
    
    return account_spending


def calculate_monthly_spending(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly spending trend.
    
    Args:
        df: Transactions dataframe with columns [ColumnNames.DATE, ColumnNames.AMOUNT]
        
    Returns:
        DataFrame with columns [ColumnNames.MONTH, ColumnNames.AMOUNT] sorted by month.
        amounts are converted to absolute values.
        
    Raises:
        FinancialCalculationError: If data is invalid
    """
    required_cols = [ColumnNames.DATE, ColumnNames.AMOUNT]
    _validate_dataframe(df, required_cols, "df")
    
    df_copy = df.copy()
    
    # Create month as datetime for proper plotting
    df_copy[ColumnNames.MONTH] = df_copy[ColumnNames.DATE].dt.to_period('M').dt.to_timestamp()
    
    monthly_spending = (
        df_copy.groupby(ColumnNames.MONTH)[ColumnNames.AMOUNT]
        .sum()
        .reset_index()
    )
    monthly_spending[ColumnNames.AMOUNT] = monthly_spending[ColumnNames.AMOUNT].apply(_convert_to_absolute)
    monthly_spending = monthly_spending.sort_values(ColumnNames.MONTH)
    
    return monthly_spending


def calculate_budget_comparison(
    df: pd.DataFrame, 
    budgets: Dict[str, float], 
    num_months: int = 1
) -> pd.DataFrame:
    """Calculate budget vs actual spending for the filtered period.
    
    Args:
        df: Transactions dataframe with columns [ColumnNames.CATEGORY, ColumnNames.AMOUNT]
        budgets: Dictionary mapping category names to monthly budget amounts
        num_months: Number of distinct months in the selected range
        
    Returns:
        DataFrame with columns:
            - Category: category name
            - Budget: Total budget for the period
            - Spent: Actual spending
            - Remaining: Budget remaining
            - Percentage: Percentage of budget spent
            
    Raises:
        FinancialCalculationError: If data is invalid
    """
    required_cols = [ColumnNames.CATEGORY, ColumnNames.AMOUNT]
    _validate_dataframe(df, required_cols, "df")
    
    if not isinstance(budgets, dict):
        raise FinancialCalculationError("budgets must be a dictionary")
    
    if num_months < 1:
        raise FinancialCalculationError("num_months must be at least 1")
    
    # Get absolute spending by category from the filtered data
    category_spending = (
        df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
        .sum()
        .apply(_convert_to_absolute)
        .to_dict()
    )
    
    budget_data = []
    for category, monthly_budget in budgets.items():
        scaled_budget = monthly_budget * num_months
        spent = category_spending.get(category, 0.0)
        remaining = scaled_budget - spent
        percentage = (spent / scaled_budget * 100) if scaled_budget > 0 else 0.0
        
        budget_data.append({
            ColumnNames.CATEGORY: category,
            'Budget': scaled_budget,
            'Spent': spent,
            'Remaining': remaining,
            'Percentage': percentage
        })
    
    return pd.DataFrame(budget_data)


def calculate_top_merchants(
    df: pd.DataFrame, 
    limit: int = None
) -> pd.DataFrame:
    """Calculate top merchants by spending.
    
    Args:
        df: Transactions dataframe with columns [ColumnNames.MERCHANT, ColumnNames.AMOUNT]
        limit: Number of top merchants to return (defaults to AnalysisConfig.TOP_MERCHANTS_LIMIT)
        
    Returns:
        DataFrame with columns [ColumnNames.MERCHANT, ColumnNames.AMOUNT] for top n merchants.
        amounts are converted to absolute values.
        
    Raises:
        FinancialCalculationError: If data is invalid
    """
    required_cols = [ColumnNames.MERCHANT, ColumnNames.AMOUNT]
    _validate_dataframe(df, required_cols, "df")
    
    if limit is None:
        limit = AnalysisConfig.TOP_MERCHANTS_LIMIT
    
    if limit < 1:
        raise FinancialCalculationError("limit must be at least 1")
    
    top_merchants = (
        df.groupby(ColumnNames.MERCHANT)[ColumnNames.AMOUNT]
        .sum()
        .apply(_convert_to_absolute)
        .sort_values(ascending=False)
        .head(limit)
        .reset_index()
    )
    
    return top_merchants


def calculate_spending_by_dow(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate spending by day of week.
    
    Args:
        df: Transactions dataframe with columns [ColumnNames.DATE, ColumnNames.AMOUNT]
        
    Returns:
        DataFrame with columns ['day_of_week', ColumnNames.AMOUNT] in weekday order.
        amounts are converted to absolute values.
        
    Raises:
        FinancialCalculationError: If data is invalid
    """
    required_cols = [ColumnNames.DATE, ColumnNames.AMOUNT]
    _validate_dataframe(df, required_cols, "df")
    
    df_copy = df.copy()
    df_copy['day_of_week'] = df_copy[ColumnNames.DATE].dt.day_name()
    
    dow_spending = (
        df_copy.groupby('day_of_week')[ColumnNames.AMOUNT]
        .sum()
        .apply(_convert_to_absolute)
        .reindex(DAYS_OF_WEEK)
        .reset_index()
    )
    
    return dow_spending


def calculate_category_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate category spending trends over time.
    
    Args:
        df: Transactions dataframe with columns [ColumnNames.DATE, ColumnNames.CATEGORY, ColumnNames.AMOUNT]
        
    Returns:
        DataFrame with columns [ColumnNames.MONTH, ColumnNames.CATEGORY, ColumnNames.AMOUNT].
        amounts are converted to absolute values.
        
    Raises:
        FinancialCalculationError: If data is invalid
    """
    required_cols = [ColumnNames.DATE, ColumnNames.CATEGORY, ColumnNames.AMOUNT]
    _validate_dataframe(df, required_cols, "df")
    
    df_copy = df.copy()
    
    # Create month as datetime for proper plotting
    df_copy[ColumnNames.MONTH] = df_copy[ColumnNames.DATE].dt.to_period('M').dt.to_timestamp()
    
    category_monthly = (
        df_copy.groupby([ColumnNames.MONTH, ColumnNames.CATEGORY])[ColumnNames.AMOUNT]
        .sum()
        .reset_index()
    )
    
    category_monthly[ColumnNames.AMOUNT] = category_monthly[ColumnNames.AMOUNT].apply(_convert_to_absolute)
    
    return category_monthly