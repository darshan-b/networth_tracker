"""Data loading and preprocessing functions."""

from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st


# Directory configuration
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'


@st.cache_data
def load_networth_data(filename: str = "Networth.csv") -> pd.DataFrame:
    """Load and preprocess net worth data from CSV.
    
    Args:
        filename: Name of CSV file to load from raw data directory
        
    Returns:
        Preprocessed DataFrame with datetime Month column and formatted strings
    """
    filepath = RAW_DATA_DIR / filename
    
    try:
        data = pd.read_csv(filepath)
        
        # Process date and amount columns
        data['Month'] = pd.to_datetime(data['Month'])
        data['Amount'] = data['Amount'].round().astype(int)
        data['Month_Str'] = data['Month'].dt.strftime('%b-%Y')
        data = data.sort_values('Month')
        
        return data
        
    except FileNotFoundError:
        st.error(f"Error: File not found at {filepath}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading {filepath}: {e}")
        return pd.DataFrame()


@st.cache_data
def load_expense_transactions(filename: str = 'transactions.csv') -> pd.DataFrame:
    """Load transaction data from CSV file.
    
    Args:
        filename: Name of CSV file to load from raw data directory
        
    Returns:
        DataFrame with transaction data including date and type columns
    """
    filepath = RAW_DATA_DIR / filename
    
    try:
        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'])
        
        # Add 'type' column if it doesn't exist
        if 'type' not in df.columns:
            df['type'] = 'expense'
        
        return df
        
    except FileNotFoundError:
        st.error(f"Error: File not found at {filepath}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading {filepath}: {e}")
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
            return dict(zip(budget_df['category'], budget_df['budget']))
        except Exception as e:
            st.warning(f"Warning: Error loading budgets from CSV: {e}. Using defaults.")
    
    # Try Excel if CSV not found or failed
    elif xlsx_path.exists():
        try:
            budget_df = pd.read_excel(xlsx_path)
            return dict(zip(budget_df['category'], budget_df['budget']))
        except Exception as e:
            st.warning(f"Warning: Error loading budgets from Excel: {e}. Using defaults.")
    
    # Return defaults if no file found
    return _get_default_budgets()


def _get_default_budgets() -> Dict[str, float]:
    """Return default budget values.
    
    Returns:
        Dictionary of default category budgets
    """
    return {
        'Housing': 1200.00,
        'Utilities': 150.00,
        'Food & Dining': 400.00,
        'Entertainment': 100.00,
        'Transportation': 200.00,
        'Miscellaneous': 300.00,
    }