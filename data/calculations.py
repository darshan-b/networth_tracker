"""Financial calculations and metrics."""

import pandas as pd


def calculate_account_info(data, accounts):
    """Calculate current values and trends for each account.
    
    Args:
        data: Full dataset
        accounts: List of account names to analyze
        
    Returns:
        Dictionary with account info including value, change, trend, type
    """
    account_info = {}
    
    for account in accounts:
        acct_data = data[data['Account'] == account].sort_values('Month')
        
        if len(acct_data) >= 2:
            current_val = acct_data.iloc[-1]['Amount']
            prev_val = acct_data.iloc[-2]['Amount']
            change = current_val - prev_val
            trend = "↑" if change > 0 else "↓" if change < 0 else "→"
        elif len(acct_data) == 1:
            current_val = acct_data.iloc[-1]['Amount']
            change = 0
            trend = "→"
        else:
            continue
        
        account_info[account] = {
            'value': current_val,
            'change': change,
            'trend': trend,
            'type': acct_data.iloc[-1]['Account Type']
        }
    
    return account_info


def calculate_metrics(latest_data, previous_data=None):
    """Calculate key financial metrics.
    
    Args:
        latest_data: DataFrame for current month
        previous_data: DataFrame for previous month (optional)
        
    Returns:
        Dictionary containing calculated metrics
    """
    # Current period calculations
    current_assets = latest_data[latest_data['Account Type'] != 'Liability']['Amount'].sum()
    current_liabilities_raw = latest_data[latest_data['Account Type'] == 'Liability']['Amount'].sum()
    current_liabilities = abs(current_liabilities_raw)
    current_net_worth = current_assets + current_liabilities_raw
    
    metrics = {
        'current_assets': current_assets,
        'current_liabilities': current_liabilities,
        'current_net_worth': current_net_worth,
        'net_worth_change': 0,
        'net_worth_pct_change': 0,
        'liabilities_change': 0,
        'liabilities_change_pct': 0,
        'debt_ratio': (current_liabilities / (current_net_worth + current_liabilities) * 100) 
                      if (current_net_worth + current_liabilities) > 0 else 0
    }
    
    # Previous period comparisons
    if previous_data is not None and not previous_data.empty:
        prev_assets = previous_data[previous_data['Account Type'] != 'Liability']['Amount'].sum()
        prev_liabilities_raw = previous_data[previous_data['Account Type'] == 'Liability']['Amount'].sum()
        prev_liabilities = abs(prev_liabilities_raw)
        prev_net_worth = prev_assets + prev_liabilities_raw
        
        metrics['net_worth_change'] = current_net_worth - prev_net_worth
        metrics['net_worth_pct_change'] = (metrics['net_worth_change'] / prev_net_worth * 100) if prev_net_worth != 0 else 0
        
        metrics['liabilities_change'] = current_liabilities - prev_liabilities
        metrics['liabilities_change_pct'] = (metrics['liabilities_change'] / prev_liabilities * 100) if prev_liabilities != 0 else 0
    
    return metrics