"""Dashboard tab rendering."""

import streamlit as st
import pandas as pd
from ui.metrics import render_key_metrics
from ui.charts import create_horizontal_bar_chart, create_donut_chart, create_top_accounts_chart
from data.calculations import calculate_metrics


def render_dashboard(filtered_df):
    """Render the complete dashboard tab.
    
    Args:
        filtered_df: Filtered dataset based on user selections
    """
    st.subheader("Financial Dashboard")
    
    # Get latest and previous month data
    latest_month = filtered_df['Month'].max()
    previous_month = filtered_df['Month'].unique()[-2] if len(filtered_df['Month'].unique()) > 1 else None
    
    latest_data = filtered_df[filtered_df['Month'] == latest_month]
    previous_data = filtered_df[filtered_df['Month'] == previous_month] if previous_month else pd.DataFrame()
    
    # Calculate metrics
    metrics = calculate_metrics(latest_data, previous_data)
    
    # Render key metrics
    render_key_metrics(metrics, not previous_data.empty)
    
    st.divider()
    
    # Category Breakdown
    st.subheader("Category Breakdown")
    
    col_cat1, col_cat2 = st.columns(2)
    
    with col_cat1:
        st.markdown("**Holdings by Category**")
        
        holdings_data = latest_data[latest_data['Account Type'] != 'Liability']
        holdings_by_category = holdings_data.groupby('Category')['Amount'].sum().sort_values(ascending=False)
        
        fig_holdings = create_horizontal_bar_chart(
            holdings_by_category, 
            "Holdings by Category", 
            'assets',
            metrics['current_assets']
        )
        st.plotly_chart(fig_holdings, use_container_width=True)
    
    with col_cat2:
        st.markdown("**Liabilities by Category**")
        
        liability_data = latest_data[latest_data['Account Type'] == 'Liability']
        
        if not liability_data.empty:
            liability_by_category = liability_data.groupby('Category')['Amount'].sum().abs().sort_values(ascending=False)
            
            fig_liabilities = create_horizontal_bar_chart(
                liability_by_category,
                "Liabilities by Category",
                'liabilities',
                metrics['current_liabilities']
            )
            st.plotly_chart(fig_liabilities, use_container_width=True)
        else:
            st.info("No liabilities recorded")
    
    st.divider()
    
    # Distribution Analysis
    st.subheader("Distribution Analysis")
    
    col_pie1, col_pie2 = st.columns(2)
    
    with col_pie1:
        st.markdown("**Account Type Distribution**")
        
        account_type_dist = latest_data.copy()
        account_type_dist['Amount_Display'] = account_type_dist['Amount'].abs()
        account_type_dist = account_type_dist.groupby('Account Type')['Amount_Display'].sum()
        
        fig_type = create_donut_chart(account_type_dist, "Account Type Distribution")
        st.plotly_chart(fig_type, use_container_width=True)
    
    with col_pie2:
        st.markdown("**Top 5 Accounts**")
        
        top_accounts = latest_data.copy()
        top_accounts['Amount'] = top_accounts['Amount'].abs()
        top_accounts = top_accounts.nlargest(5, 'Amount')[['Account', 'Amount', 'Category']]
        
        fig_top = create_top_accounts_chart(top_accounts)
        st.plotly_chart(fig_top, use_container_width=True)
