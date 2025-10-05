"""Data validation utilities for consistent input checking."""

import streamlit as st
import pandas as pd
from typing import List, Optional, Tuple


def validate_dataframe(
    df: Optional[pd.DataFrame],
    required_columns: Optional[List[str]] = None,
    min_rows: int = 1,
    context: str = ""
) -> bool:
    """
    Centralized dataframe validation with user feedback.
    
    Args:
        df: DataFrame to validate
        required_columns: List of column names that must be present
        min_rows: Minimum number of rows required
        context: Context string for error messages (e.g., "expense data")
        
    Returns:
        True if validation passes, False otherwise (with st.warning/error displayed)
    """
    # Check if dataframe exists and is not empty
    if df is None or df.empty:
        context_msg = f" for {context}" if context else ""
        st.warning(f"No data available{context_msg}.")
        return False
    
    # Check for required columns
    if required_columns:
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            st.error(f"Missing required columns: {', '.join(missing)}")
            if context:
                st.info(f"Required for {context}: {', '.join(required_columns)}")
            return False
    
    # Check minimum row count
    if len(df) < min_rows:
        st.warning(
            f"Insufficient data. Need at least {min_rows} row(s), "
            f"but only {len(df)} found."
        )
        return False
    
    return True


def validate_budget_config(budgets: dict, context: str = "budget data") -> bool:
    """
    Validate budget configuration dictionary.
    
    Args:
        budgets: Dictionary of budgets by category
        context: Context string for error messages
        
    Returns:
        True if validation passes, False otherwise
    """
    if not isinstance(budgets, dict):
        st.error(f"Invalid {context}. Expected dictionary format.")
        return False
    
    if len(budgets) == 0:
        st.warning(f"No {context} configured.")
        return False
    
    # Check for non-negative budget values
    invalid_budgets = {k: v for k, v in budgets.items() if v < 0}
    if invalid_budgets:
        st.error(f"Negative budget values found: {invalid_budgets}")
        return False
    
    return True


def validate_positive_integer(value: int, param_name: str = "parameter") -> bool:
    """
    Validate that a value is a positive integer.
    
    Args:
        value: Value to validate
        param_name: Parameter name for error messages
        
    Returns:
        True if validation passes, False otherwise
    """
    if value < 1:
        st.error(f"Invalid {param_name}: {value}. Must be at least 1.")
        return False
    return True


def validate_date_range(
    df: pd.DataFrame,
    date_column: str = 'date',
    min_periods: int = 2
) -> Tuple[bool, str]:
    """
    Validate that dataframe has sufficient date range for analysis.
    
    Args:
        df: DataFrame with date column
        date_column: Name of the date column
        min_periods: Minimum number of unique periods required
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if date_column not in df.columns:
        return False, f"Date column '{date_column}' not found"
    
    unique_periods = df[date_column].nunique()
    
    if unique_periods < min_periods:
        return False, (
            f"Need at least {min_periods} period(s) for analysis. "
            f"Currently have {unique_periods}."
        )
    
    return True, ""


def check_data_quality(df: pd.DataFrame, context: str = "") -> None:
    """
    Display data quality warnings (non-blocking).
    
    Args:
        df: DataFrame to check
        context: Context for warnings
    """
    context_prefix = f"{context}: " if context else ""
    
    # Check for null values
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0]
    
    if not null_cols.empty:
        st.warning(
            f"{context_prefix}Found missing values in columns: "
            f"{', '.join(null_cols.index.tolist())}"
        )
    
    # Check for duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        st.info(f"{context_prefix}Found {duplicates} duplicate row(s)")