"""Data loading and preprocessing functions."""

from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import streamlit as st
from constants import ColumnNames


# Directory configuration
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'


def _show_missing_file_error(filepath: Path, context: str) -> None:
    """Display a consistent missing-file message with recovery guidance."""
    st.error(f"{context} file not found.")
    st.caption(f"Expected path: `{filepath}`")
    st.info("Add the file in the expected location or update the loader configuration before retrying.")


def _show_load_error(filepath: Path, context: str, error: Exception) -> None:
    """Display a consistent data-load failure message."""
    st.error(f"Unable to load {context.lower()}.")
    st.caption(f"Source: `{filepath}`")
    st.info(f"Check the file format, required columns, and sheet names. Details: {error}")


@st.cache_data
def load_networth_data(filename: str = "Networth.csv") -> pd.DataFrame:
    """Load and preprocess net worth data from CSV.
    
    Args:
        filename: Name of CSV file to load from raw data directory
        
    Returns:
        Preprocessed DataFrame with datetime month column and formatted strings
    """
    filepath = RAW_DATA_DIR / filename
    
    try:
        data = pd.read_csv(filepath)
        
        # Process date and amount columns
        data[ColumnNames.MONTH] = pd.to_datetime(data[ColumnNames.MONTH])
        data[ColumnNames.AMOUNT] = data[ColumnNames.AMOUNT].round().astype(int)
        data['month_Str'] = data[ColumnNames.MONTH].dt.strftime('%b-%Y')
        data = data.sort_values(ColumnNames.MONTH)
        
        return data
        
    except FileNotFoundError:
        _show_missing_file_error(filepath, "Net worth data")
        return pd.DataFrame()
    except Exception as e:
        _show_load_error(filepath, "Net worth data", e)
        return pd.DataFrame()


@st.cache_data
def load_expense_transactions(filename: str = 'transactions.xlsx') -> pd.DataFrame:
    """Load transaction data from CSV file.
    
    Args:
        filename: Name of CSV file to load from raw data directory
        
    Returns:
        DataFrame with transaction data including date and type columns
    """
    filepath = RAW_DATA_DIR / filename
    
    try:
        df = pd.read_excel(filepath)
        df[ColumnNames.DATE] = pd.to_datetime(df[ColumnNames.DATE])
        
        # Add 'type' column if it doesn't exist
        if 'type' not in df.columns:
            df['type'] = 'expense'
        
        return df
        
    except FileNotFoundError:
        _show_missing_file_error(filepath, "Expense transactions")
        return pd.DataFrame()
    except Exception as e:
        _show_load_error(filepath, "Expense transactions", e)
        return pd.DataFrame()


@st.cache_data
def load_budgets(filename: str = 'budgets.csv') -> Dict[str, float]:
    """Load budget data from CSV or Excel file.
    
    Args:
        filename: Name of budget file (supports .csv or .xlsx)
        
    Returns:
        Dictionary mapping category names to budget amounts
    """
    # Check for CSV first
    csv_path = DATA_DIR / 'budgets.csv'
    xlsx_path = DATA_DIR / 'budgets.xlsx'
    
    # Try CSV first
    if csv_path.exists():
        try:
            budget_df = pd.read_csv(csv_path)
            return dict(zip(budget_df[ColumnNames.DATE], budget_df['budget']))
        except Exception as e:
            st.warning("Budget file could not be loaded from CSV. Using default budget values.")
            st.caption(f"Source: `{csv_path}`")
            st.info(f"Check for `date` and `budget` columns. Details: {e}")
    
    # Try Excel if CSV not found or failed
    elif xlsx_path.exists():
        try:
            budget_df = pd.read_excel(xlsx_path)
            return dict(zip(budget_df[ColumnNames.DATE], budget_df['budget']))
        except Exception as e:
            st.warning("Budget file could not be loaded from Excel. Using default budget values.")
            st.caption(f"Source: `{xlsx_path}`")
            st.info(f"Check for `date` and `budget` columns. Details: {e}")
    
    # Return defaults if no file found
    return _get_default_budgets()


@st.cache_data
def load_stock_data(filename: str = 'stock_positions.xlsx') -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Load stock trading and historical sheets from the Excel file."""
    file_path = RAW_DATA_DIR / filename
    
    try:
        trading_log = pd.read_excel(file_path, sheet_name='trading_log')
        try:
            historical = pd.read_excel(file_path, sheet_name='Historical_Tracking')
        except ValueError:
            historical = pd.DataFrame()
        
        # Convert dates
        trading_log['Date'] = pd.to_datetime(trading_log['Date'])
        if not historical.empty:
            historical['Date'] = pd.to_datetime(historical['Date'])
        
        return trading_log, historical
    except FileNotFoundError:
        _show_missing_file_error(file_path, "Stock tracker")
        return None, None
    except Exception as e:
        _show_load_error(file_path, "Stock tracker data", e)
        return None, None


# if you don't want to provide a file for budget set it here with whatever categories you have
def _get_default_budgets() -> Dict[str, float]:
    """Return default budget values.
    
    Returns:
        Dictionary of default category budgets
    """
    return {
        'Housing': 1200.00,
        'Utilities': 150.00,
        'Food & Dining': 350.00,
        'Entertainment': 100.00,
        'Transportation': 200.00,
        'Miscellaneous': 200.00,
    }
