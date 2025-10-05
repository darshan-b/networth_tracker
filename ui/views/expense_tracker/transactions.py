"""Transactions tab for expense tracker.

Provides transaction filtering, search, and detailed view of all transactions.
"""

import streamlit as st
import pandas as pd


def render_transactions_tab(df):
    """
    Render the transactions management tab with filtering and search capabilities.
    
    Args:
        df (pd.DataFrame): Transactions dataframe (includes both expenses and income)
        
    Returns:
        None
    """
    st.subheader("Transactions")
    
    if df.empty:
        st.info("No transactions available for the selected period.")
        return
    
    # Render filters
    df_filtered = _apply_transaction_filters(df)
    
    if df_filtered.empty:
        st.warning("No transactions match the selected filters.")
        return
    
    # Display transaction table
    _render_transaction_table(df_filtered)
    
    st.divider()
    
    # Display summary metrics
    _render_transaction_summary(df_filtered)


def _apply_transaction_filters(df):
    """
    Render filter controls and apply filtering logic.
    
    Args:
        df (pd.DataFrame): Original transactions dataframe
        
    Returns:
        pd.DataFrame: Filtered transactions dataframe
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        account_filter = st.multiselect(
            "Filter by Account", 
            options=sorted(df['account'].unique()),
            default=list(df['account'].unique())
        )
    
    with col2:
        category_filter = st.multiselect(
            "Filter by Category",
            options=sorted(df['category'].unique()),
            default=list(df['category'].unique())
        )
    
    with col3:
        search_merchant = st.text_input("Search Merchant", "")
    
    # Apply filters
    df_filtered = df[
        (df['account'].isin(account_filter)) &
        (df['category'].isin(category_filter))
    ]
    
    if search_merchant:
        df_filtered = df_filtered[
            df_filtered['merchant'].str.contains(
                search_merchant, 
                case=False, 
                na=False
            )
        ]
    
    return df_filtered


def _render_transaction_table(df_filtered):
    """
    Render the transactions table with proper formatting.
    
    Args:
        df_filtered (pd.DataFrame): Filtered transactions dataframe
    """
    df_display = df_filtered.sort_values('date', ascending=False).copy()
    
    # Create display amount column (absolute value for expenses, positive for income)
    df_display['display_amount'] = df_display.apply(
        lambda row: abs(row['amount']) if row['category'] != 'Income' else row['amount'], 
        axis=1
    )
    
    st.dataframe(
        df_display[['date', 'merchant', 'category', 'account', 'display_amount']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "display_amount": st.column_config.NumberColumn(
                "Amount", 
                format="$%.2f"
            ),
            "date": st.column_config.DateColumn("Date"),
        }
    )


def _render_transaction_summary(df_filtered):
    """
    Display summary metrics for filtered transactions.
    
    Args:
        df_filtered (pd.DataFrame): Filtered transactions dataframe
    """
    col1, col2 = st.columns(2)
    
    with col1:
        expenses_filtered = df_filtered[df_filtered['category'] != 'Income']
        expenses_total = abs(expenses_filtered['amount'].sum())
        st.metric("Total Expenses (Filtered)", f"${expenses_total:,.2f}")
    
    with col2:
        income_filtered = df_filtered[df_filtered['category'] == 'Income']
        income_total = income_filtered['amount'].sum()
        st.metric("Total Income (Filtered)", f"${income_total:,.2f}")