"""Data loading and preprocessing functions."""

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import streamlit as st
from constants import ColumnNames


# Directory configuration
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
DEFAULT_BUDGET_FILENAME = "budgets.csv"
EMPTY_DF = pd.DataFrame()


def _resolve_raw_path(filename: str) -> Path:
    """Return a path inside the raw data directory."""
    return RAW_DATA_DIR / filename


def _resolve_data_path(filename: str) -> Path:
    """Return a path inside the data directory."""
    return DATA_DIR / filename


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


def _load_excel_sheet(filepath: Path, sheet_name: str, context: str) -> pd.DataFrame:
    """Load a single Excel sheet with consistent error handling."""
    try:
        return pd.read_excel(filepath, sheet_name=sheet_name)
    except FileNotFoundError:
        _show_missing_file_error(filepath, context)
    except ValueError as error:
        st.error(f"Required sheet `{sheet_name}` not found for {context.lower()}.")
        st.caption(f"Source: `{filepath}`")
        st.info(f"Add the missing sheet and retry. Details: {error}")
    except Exception as error:
        _show_load_error(filepath, context, error)

    return EMPTY_DF.copy()


@st.cache_data
def load_networth_data(filename: str = "Networth.csv") -> pd.DataFrame:
    """Load and preprocess net worth data from CSV.
    
    Args:
        filename: Name of CSV file to load from raw data directory
        
    Returns:
        Preprocessed DataFrame with datetime month column and formatted strings
    """
    filepath = _resolve_raw_path(filename)
    
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
        return EMPTY_DF.copy()
    except Exception as e:
        _show_load_error(filepath, "Net worth data", e)
        return EMPTY_DF.copy()


@st.cache_data
def load_expense_transactions(filename: str = 'transactions.xlsx') -> pd.DataFrame:
    """Load transaction data from CSV file.
    
    Args:
        filename: Name of CSV file to load from raw data directory
        
    Returns:
        DataFrame with transaction data including date and type columns
    """
    filepath = _resolve_raw_path(filename)
    
    try:
        df = pd.read_excel(filepath)
        df[ColumnNames.DATE] = pd.to_datetime(df[ColumnNames.DATE])
        
        # Add 'type' column if it doesn't exist
        if 'type' not in df.columns:
            df['type'] = 'expense'
        
        return df
        
    except FileNotFoundError:
        _show_missing_file_error(filepath, "Expense transactions")
        return EMPTY_DF.copy()
    except Exception as e:
        _show_load_error(filepath, "Expense transactions", e)
        return EMPTY_DF.copy()


@st.cache_data
def load_budgets(filename: str = DEFAULT_BUDGET_FILENAME) -> Dict[str, float]:
    """Load budget data from CSV or Excel file.
    
    Args:
        filename: Name of budget file (supports .csv or .xlsx)
        
    Returns:
        Dictionary mapping category names to budget amounts
    """
    csv_path = _resolve_data_path(filename)
    xlsx_name = Path(filename).with_suffix('.xlsx').name
    xlsx_path = _resolve_data_path(xlsx_name)
    
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
def load_stock_data(filename: str = 'stock_positions.xlsx') -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load stock trading and historical sheets from the Excel file."""
    file_path = _resolve_raw_path(filename)

    trading_log = _load_excel_sheet(file_path, 'trading_log', "Stock tracker data")
    historical = _load_excel_sheet(file_path, 'Historical_Tracking', "Stock tracker data")

    if not trading_log.empty and 'Date' in trading_log.columns:
        trading_log['Date'] = pd.to_datetime(trading_log['Date'])

    if not historical.empty and 'Date' in historical.columns:
        historical['Date'] = pd.to_datetime(historical['Date'])

    return trading_log, historical


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
