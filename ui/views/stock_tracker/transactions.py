"""Transactions tab for portfolio analysis.

This module provides transaction history visualization and analysis.
"""

import streamlit as st
import pandas as pd

from ui.charts import create_transaction_timeline


def render(trading_log_df: pd.DataFrame) -> None:
    """Render the transaction history tab.
    
    Args:
        trading_log_df: Trading log DataFrame (already filtered by accounts)
    """
    try:
        st.header("Transaction History")
        
        if trading_log_df is None or trading_log_df.empty:
            st.info("No transaction data available for selected filters.")
            return
        
        # Display transaction summary metrics
        _render_transaction_summary(trading_log_df)
        
        # Display transaction timeline chart
        st.subheader("Transaction Timeline")
        _render_transaction_timeline(trading_log_df)
        
        # Display transaction type breakdown
        st.subheader("Transaction Summary by Type")
        _render_transaction_breakdown(trading_log_df)
        
        # Display recent transactions
        st.subheader("Recent Transactions")
        _render_recent_transactions(trading_log_df)
        
        # Display all transactions with filters
        st.subheader("All Transactions")
        _render_all_transactions(trading_log_df)
        
    except Exception as e:
        st.error(f"Error rendering transaction history: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_transaction_summary(df: pd.DataFrame) -> None:
    """Render summary metrics for transactions.
    
    Args:
        df: Trading log DataFrame
    """
    total_transactions = len(df)
    total_amount = df['Amount'].sum()
    
    # Calculate buy/sell totals
    buys = df[df['Transaction Type'] == 'Buy']
    sells = df[df['Transaction Type'] == 'Sell']
    
    total_invested = buys['Amount'].sum()
    total_proceeds = sells['Amount'].sum()
    
    # Get date range
    if 'Date' in df.columns:
        date_range = (df['Date'].max() - df['Date'].min()).days
    else:
        date_range = 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Transactions", total_transactions)
    
    with col2:
        st.metric("Total Invested", f"${total_invested:,.2f}")
    
    with col3:
        st.metric("Total Proceeds", f"${total_proceeds:,.2f}")
    
    with col4:
        net_flow = total_invested - total_proceeds
        st.metric("Net Flow", f"${net_flow:,.2f}")
    
    st.divider()


def _render_transaction_timeline(df: pd.DataFrame) -> None:
    """Render transaction timeline chart.
    
    Args:
        df: Trading log DataFrame
    """
    try:
        if 'Date' not in df.columns:
            st.warning("Date information not available for timeline.")
            return
        
        fig = create_transaction_timeline(df)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error creating timeline chart: {str(e)}")


def _render_transaction_breakdown(df: pd.DataFrame) -> None:
    """Render transaction type breakdown table.
    
    Args:
        df: Trading log DataFrame
    """
    if 'Transaction Type' not in df.columns:
        st.warning("Transaction type information not available.")
        return
    
    # Group by transaction type
    trans_summary = df.groupby('Transaction Type').agg({
        'Amount': ['sum', 'count', 'mean'],
        'Quantity': 'sum'
    }).reset_index()
    
    trans_summary.columns = [
        'Transaction Type', 
        'Total Amount', 
        'Count', 
        'Avg Amount',
        'Total Quantity'
    ]
    
    # Display formatted table
    st.dataframe(
        trans_summary.style.format({
            'Total Amount': '${:,.2f}',
            'Count': '{:.0f}',
            'Avg Amount': '${:,.2f}',
            'Total Quantity': '{:.4f}'
        }),
        use_container_width=True,
        hide_index=True
    )


def _render_recent_transactions(df: pd.DataFrame, n: int = 20) -> None:
    """Render recent transactions table.
    
    Args:
        df: Trading log DataFrame
        n: Number of recent transactions to display
    """
    if 'Date' not in df.columns:
        st.warning("Date information not available.")
        return
    
    recent = df.sort_values('Date', ascending=False).head(n)
    
    # Select relevant columns
    display_columns = []
    for col in ['Date', 'ticker', 'Transaction Type', 'Quantity', 'Amount']:
        if col in recent.columns:
            display_columns.append(col)
    
    if not display_columns:
        st.warning("No transaction data to display.")
        return
    
    recent_display = recent[display_columns].copy()
    
    # Format the dataframe
    format_dict = {}
    if 'Quantity' in recent_display.columns:
        format_dict['Quantity'] = '{:.4f}'
    if 'Amount' in recent_display.columns:
        format_dict['Amount'] = '${:,.2f}'
    
    st.dataframe(
        recent_display.style.format(format_dict),
        use_container_width=True,
        hide_index=True,
        height=400
    )


def _render_all_transactions(df: pd.DataFrame) -> None:
    """Render all transactions with optional filtering.
    
    Args:
        df: Trading log DataFrame
    """
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    filtered_df = df.copy()
    
    # Transaction type filter
    if 'Transaction Type' in df.columns:
        with col1:
            trans_types = ['All'] + sorted(df['Transaction Type'].unique().tolist())
            selected_type = st.selectbox(
                "Transaction Type",
                trans_types,
                key='trans_type_filter'
            )
            
            if selected_type != 'All':
                filtered_df = filtered_df[
                    filtered_df['Transaction Type'] == selected_type
                ]
    
    # Symbol filter
    if 'ticker' in df.columns:
        with col2:
            symbols = ['All'] + sorted(df['ticker'].unique().tolist())
            selected_symbol = st.selectbox(
                "Symbol",
                symbols,
                key='symbol_filter'
            )
            
            if selected_symbol != 'All':
                filtered_df = filtered_df[filtered_df['ticker'] == selected_symbol]
    
    # Sort order
    with col3:
        sort_order = st.selectbox(
            "Sort By",
            ['Date (Newest)', 'Date (Oldest)', 'Amount (Highest)', 'Amount (Lowest)'],
            key='sort_order'
        )
    
    # Apply sorting
    if 'Date' in filtered_df.columns:
        if sort_order == 'Date (Newest)':
            filtered_df = filtered_df.sort_values('Date', ascending=False)
        elif sort_order == 'Date (Oldest)':
            filtered_df = filtered_df.sort_values('Date', ascending=True)
    
    if 'Amount' in filtered_df.columns:
        if sort_order == 'Amount (Highest)':
            filtered_df = filtered_df.sort_values('Amount', ascending=False)
        elif sort_order == 'Amount (Lowest)':
            filtered_df = filtered_df.sort_values('Amount', ascending=True)
    
    # Display filtered results
    st.caption(f"Showing {len(filtered_df)} of {len(df)} transactions")
    
    # Select display columns
    display_columns = []
    for col in ['Date', 'ticker', 'Transaction Type', 'Quantity', 'Amount', 'Price']:
        if col in filtered_df.columns:
            display_columns.append(col)
    
    if display_columns:
        display_df = filtered_df[display_columns].copy()
        
        # Format the dataframe
        format_dict = {}
        if 'Quantity' in display_df.columns:
            format_dict['Quantity'] = '{:.4f}'
        if 'Amount' in display_df.columns:
            format_dict['Amount'] = '${:,.2f}'
        if 'Price' in display_df.columns:
            format_dict['Price'] = '${:.2f}'
        
        st.dataframe(
            display_df.style.format(format_dict),
            use_container_width=True,
            hide_index=True,
            height=500
        )
    else:
        st.warning("No transaction data to display.")