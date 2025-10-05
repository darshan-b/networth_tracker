"""Data filtering functions for the Personal Finance Tracker.

This module provides pure data filtering functions for both Net Worth and Expense tracking,
with comprehensive error handling and input validation.
"""

from datetime import datetime
from typing import List, Optional, Tuple, Union

import pandas as pd
import streamlit as st

# Constants for date range options
DATE_RANGE_LAST_7 = "Last 7 days"
DATE_RANGE_LAST_14 = "Last 14 days"
DATE_RANGE_LAST_30 = "Last 30 days"
DATE_RANGE_THIS_MONTH = "This month"
DATE_RANGE_LAST_MONTH = "Last month"
DATE_RANGE_THIS_YEAR = "This year"
DATE_RANGE_LAST_YEAR = "Last year"
DATE_RANGE_CUSTOM = "Custom range"

# Column name constants
COL_ACCOUNT_TYPE = 'Account Type'
COL_CATEGORY = 'Category'
COL_ACCOUNT = 'Account'
COL_DATE = 'date'
COL_CATEGORY_EXPENSE = 'category'


def filter_data(data: pd.DataFrame, account_types: List[str], categories: List[str], accounts: List[str]) -> pd.DataFrame:
    """Apply all filters to net worth dataset with validation.
    
    Args:
        data: Full dataset
        account_types: List of account types to include
        categories: List of categories to include
        accounts: List of specific accounts to include
        
    Returns:
        Filtered DataFrame
        
    Raises:
        ValueError: If data is None or empty
        KeyError: If required columns are missing
    """
    try: 
        # Apply filters
        filtered_df = data[
            data[COL_ACCOUNT_TYPE].isin(account_types) &
            data[COL_CATEGORY].isin(categories) &
            data[COL_ACCOUNT].isin(accounts)
        ]
        
        return filtered_df
        
    except Exception as e:
        st.error(f" Error filtering data: {str(e)}")
        raise


def get_filtered_accounts(data: pd.DataFrame, account_types: List[str], categories: List[str]) -> List[str]:
    """Get list of accounts matching type and category filters.
    
    Args:
        data: Full dataset
        account_types: List of account types to include
        categories: List of categories to include
        
    Returns:
        List of account names
        
    Raises:
        ValueError: If data is None or empty
        KeyError: If required columns are missing
    """
    try:
        # Filter accounts
        if account_types and categories:
            accounts = data[
                data[COL_ACCOUNT_TYPE].isin(account_types) & 
                data[COL_CATEGORY].isin(categories)
            ][COL_ACCOUNT].unique().tolist()
        else:
            accounts = data[COL_ACCOUNT].unique().tolist()
        
        return accounts
        
    except Exception as e:
        st.error(f" Error getting filtered accounts: {str(e)}")
        raise


# Expense Tracker Filtering Functions
def get_date_range_options() -> List[str]:
    """Get standard date range options for expense filtering.
    
    Returns:
        List of date range option strings
    """
    return [
        DATE_RANGE_LAST_7,
        DATE_RANGE_LAST_14,
        DATE_RANGE_LAST_30,
        DATE_RANGE_THIS_MONTH,
        DATE_RANGE_LAST_MONTH,
        DATE_RANGE_THIS_YEAR,
        DATE_RANGE_LAST_YEAR,
        DATE_RANGE_CUSTOM
    ]


def calculate_date_range(date_option: str) -> Optional[Tuple[datetime, datetime]]:
    """Calculate start and end dates based on the selected option.
    
    Args:
        date_option: Selected date range option from get_date_range_options()
        
    Returns:
        Tuple of (start_date, end_date) or None for custom range
        
    Raises:
        ValueError: If date_option is invalid
    """
    try:
        if not date_option:
            st.warning(" No date option provided")
            return None
        
        if date_option not in get_date_range_options():
            st.error(f" Invalid date option: {date_option}")
            raise ValueError(f"Invalid date_option: {date_option}")
        
        if date_option == DATE_RANGE_CUSTOM:
            return None
        
        today = datetime.now()
        
        if date_option == DATE_RANGE_LAST_7:
            return (today - pd.Timedelta(days=7), today)
            
        elif date_option == DATE_RANGE_LAST_14:
            return (today - pd.Timedelta(days=14), today)
            
        elif date_option == DATE_RANGE_LAST_30:
            return (today - pd.Timedelta(days=30), today)
            
        elif date_option == DATE_RANGE_THIS_MONTH:
            start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return (start, today)
            
        elif date_option == DATE_RANGE_LAST_MONTH:
            first_of_this_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = first_of_this_month - pd.Timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return (last_month_start, last_month_end)
            
        elif date_option == DATE_RANGE_THIS_YEAR:
            start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            return (start, today)
            
        elif date_option == DATE_RANGE_LAST_YEAR:
            start = today.replace(year=today.year-1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = today.replace(year=today.year-1, month=12, day=31, hour=23, minute=59, second=59)
            return (start, end)
        
        return None
        
    except Exception as e:
        st.error(f" Error calculating date range: {str(e)}")
        raise


def filter_by_date_range(df: pd.DataFrame, start_date: Union[datetime, pd.Timestamp], end_date: Union[datetime, pd.Timestamp]) -> pd.DataFrame:
    """Filter dataframe by date range with validation.
    
    Args:
        df: DataFrame to filter (must have 'date' column)
        start_date: Start date (datetime or date)
        end_date: End date (datetime or date)
        
    Returns:
        Filtered DataFrame
        
    Raises:
        ValueError: If inputs are invalid
        KeyError: If 'date' column is missing
    """
    try:
        if COL_DATE not in df.columns:
            st.error(f" '{COL_DATE}' column not found in data")
            raise KeyError(f"'{COL_DATE}' column not found in DataFrame")
        
        if start_date is None or end_date is None:
            st.info(" No date range specified, returning all data")
            return df.copy()
        
        if start_date > end_date:
            st.warning(f" Start date is after end date, swapping dates")
            start_date, end_date = end_date, start_date
        
        # Filter by date range
        filtered_df = df[(df[COL_DATE] >= start_date) & (df[COL_DATE] <= end_date)]
        
        return filtered_df
        
    except Exception as e:
        st.error(f" Error filtering by date range: {str(e)}")
        raise


def filter_expenses(df: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for expenses only, excluding Income.
    
    Args:
        df: Transactions dataframe (must have 'category' column)
        
    Returns:
        DataFrame with expenses only (category != 'Income')
        
    Raises:
        KeyError: If 'category' column is missing
    """
    try:        
        if COL_CATEGORY_EXPENSE not in df.columns:
            st.error(f" '{COL_CATEGORY_EXPENSE}' column not found in data")
            raise KeyError(f"'{COL_CATEGORY_EXPENSE}' column not found in DataFrame")
        
        # Filter out income
        filtered_df = df[df[COL_CATEGORY_EXPENSE] != 'Income']
        
        return filtered_df
        
    except Exception as e:
        st.error(f" Error filtering expenses: {str(e)}")
        raise
