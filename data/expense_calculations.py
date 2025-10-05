"""Calculations and aggregations for expense data.

Note: Transactions are stored with negative amounts for expenses and positive for income.
Income is identified by category == 'Income'.
"""

import pandas as pd
from datetime import datetime


def calculate_expense_summary(df, budgets, num_months=1):
    """Calculate summary statistics for expenses.
    
    Args:
        df: Transactions dataframe (already filtered for expenses, excluding Income)
        budgets: Dictionary of monthly budgets by category
        num_months: Number of distinct months in the selected range
        
    Returns:
        Dictionary with summary statistics
    """
    # Use absolute values for expenses
    total_spent = abs(df['amount'].sum())
    total_budget = sum(budgets.values()) * num_months
    remaining = total_budget - total_spent
    num_transactions = len(df)
    
    return {
        'total_spent': total_spent,
        'total_budget': total_budget,
        'remaining': remaining,
        'num_transactions': num_transactions,
        'avg_transaction': total_spent / num_transactions if num_transactions > 0 else 0
    }


def calculate_category_spending(df):
    """Calculate spending by category.
    
    Args:
        df: Transactions dataframe (already filtered for expenses)
        
    Returns:
        DataFrame with category spending (positive amounts)
    """
    category_spending = df.groupby('category')['amount'].sum().reset_index()
    # Convert to absolute values for display
    category_spending['amount'] = abs(category_spending['amount'])
    category_spending = category_spending.sort_values('amount', ascending=False)
    return category_spending


def calculate_account_spending(df):
    """Calculate spending by account.
    
    Args:
        df: Transactions dataframe (already filtered for expenses)
        
    Returns:
        DataFrame with account spending (positive amounts)
    """
    account_spending = df.groupby('account')['amount'].sum().reset_index()
    # Convert to absolute values for display
    account_spending['amount'] = abs(account_spending['amount'])
    account_spending = account_spending.sort_values('amount', ascending=False)
    return account_spending


def calculate_monthly_spending(df):
    """Calculate monthly spending trend.
    
    Args:
        df: Transactions dataframe (already filtered for expenses)
        
    Returns:
        DataFrame with monthly spending (positive amounts)
    """
    df_copy = df.copy()
    # Create month as datetime for proper plotting
    df_copy['month'] = df_copy['date'].dt.to_period('M').dt.to_timestamp()
    monthly_spending = df_copy.groupby('month')['amount'].sum().reset_index()
    # Convert to absolute values for display
    monthly_spending['amount'] = abs(monthly_spending['amount'])
    monthly_spending = monthly_spending.sort_values('month')
    return monthly_spending


def calculate_budget_comparison(df, budgets, num_months=1):
    """Calculate budget vs actual for the filtered period.
    
    Args:
        df: Transactions dataframe (already filtered for expenses and date range)
        budgets: Dictionary of monthly budgets by category
        num_months: Number of distinct months in the selected range
        
    Returns:
        DataFrame with budget comparison
    """
    # Get absolute spending by category from the filtered data
    category_spending = df.groupby('category')['amount'].sum().apply(abs).to_dict()
    
    budget_data = []
    for category, monthly_budget in budgets.items():
        scaled_budget = monthly_budget * num_months
        spent = category_spending.get(category, 0)
        budget_data.append({
            'Category': category,
            'Budget': scaled_budget,
            'Spent': spent,
            'Remaining': scaled_budget - spent,
            'Percentage': (spent / scaled_budget * 100) if scaled_budget > 0 else 0
        })
    
    return pd.DataFrame(budget_data)


def calculate_top_merchants(df, n=10):
    """Calculate top merchants by spending.
    
    Args:
        df: Transactions dataframe (already filtered for expenses)
        n: Number of top merchants to return
        
    Returns:
        DataFrame with top merchants (positive amounts)
    """
    top_merchants = df.groupby('merchant')['amount'].sum().apply(abs).sort_values(ascending=False).head(n).reset_index()
    return top_merchants


def calculate_spending_by_dow(df):
    """Calculate spending by day of week.
    
    Args:
        df: Transactions dataframe (already filtered for expenses)
        
    Returns:
        DataFrame with spending by day of week (positive amounts)
    """
    df_copy = df.copy()
    df_copy['day_of_week'] = df_copy['date'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_spending = df_copy.groupby('day_of_week')['amount'].sum().apply(abs).reindex(day_order).reset_index()
    return dow_spending


def calculate_category_trends(df):
    """Calculate category spending trends over time.
    
    Args:
        df: Transactions dataframe (already filtered for expenses)
        
    Returns:
        DataFrame with category trends (positive amounts)
    """
    df_copy = df.copy()
    # Create month as datetime for proper plotting
    df_copy['month'] = df_copy['date'].dt.to_period('M').dt.to_timestamp()
    category_monthly = df_copy.groupby(['month', 'category'])['amount'].sum().reset_index()
    # Convert to absolute values for display
    category_monthly['amount'] = abs(category_monthly['amount'])
    return category_monthly