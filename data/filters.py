"""Data filtering functions."""

import pandas as pd


def filter_data(data, account_types, categories, accounts):
    """Apply all filters to dataset.
    
    Args:
        data: Full dataset
        account_types: List of account types to include
        categories: List of categories to include
        accounts: List of specific accounts to include
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = data[
        data['Account Type'].isin(account_types) &
        data['Category'].isin(categories) &
        data['Account'].isin(accounts)
    ]
    
    return filtered_df


def get_filtered_accounts(data, account_types, categories):
    """Get list of accounts matching type and category filters.
    
    Args:
        data: Full dataset
        account_types: List of account types to include
        categories: List of categories to include
        
    Returns:
        List of account names
    """
    if account_types and categories:
        accounts = data[
            data['Account Type'].isin(account_types) & 
            data['Category'].isin(categories)
        ]['Account'].unique().tolist()
    else:
        accounts = data['Account'].unique().tolist()
    
    return accounts