"""Data loading and management for expense tracker."""

import pandas as pd
import streamlit as st
import os


@st.cache_data
def load_transactions():
    """Load transaction data from Excel/CSV file (cached for performance).
    
    Returns:
        DataFrame with transaction data
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_path, 'transactions.csv')
    
    try:
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # Add 'type' column if it doesn't exist
        if 'type' not in df.columns:
            df['type'] = 'expense'
        
        return df
    except Exception as e:
        st.error(f"❌ Error loading {csv_path}: {e}")


@st.cache_data
def load_budgets():
    """Load budget data from Excel/CSV file (cached for performance).
    
    Returns:
        Dictionary with category: budget mappings
    """
    budget_excel_path = 'data/budgets.xlsx'
    budget_csv_path = 'data/budgets.csv'
    
    if os.path.exists(budget_excel_path):
        try:
            budget_df = pd.read_excel(budget_excel_path)
            return dict(zip(budget_df['category'], budget_df['budget']))
        except Exception as e:
            st.warning(f"⚠️ Error loading budgets: {e}. Using defaults.")
            return _get_default_budgets()
    elif os.path.exists(budget_csv_path):
        try:
            budget_df = pd.read_csv(budget_csv_path)
            return dict(zip(budget_df['category'], budget_df['budget']))
        except Exception as e:
            st.warning(f"⚠️ Error loading budgets: {e}. Using defaults.")
            return _get_default_budgets()
    else:
        return _get_default_budgets()


def _get_default_budgets():
    """Return default budget values."""
    return {
        'Housing': 1200.00,
        'Utilities': 150.00,
        'Food & Dining': 400.00,
        'Entertainment': 100.00,
        'Transportation': 200.00,
        'Miscellaneous': 300.00,
    }


# Legacy compatibility - for existing code that might use these
def get_transactions():
    """Get transactions dataframe (read-only)."""
    return load_transactions()


def get_budgets():
    """Get budgets dictionary (read-only)."""
    return load_budgets()