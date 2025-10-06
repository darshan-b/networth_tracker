"""Dashboard tab rendering."""

import streamlit as st
import pandas as pd
from ui.components.utils import render_metric_cards
from ui.charts import create_horizontal_bar_chart, create_donut_chart, create_top_accounts_chart
from data.calculations import calculate_metrics
from constants import ColumnNames


def render_dashboard(filtered_df):
    """Render the complete dashboard tab.
    
    Args:
        filtered_df: Filtered dataset based on user selections
    """
    st.subheader("Financial Dashboard")
    
    # Get latest and previous month data
    latest_month = filtered_df[ColumnNames.MONTH].max()
    previous_month = filtered_df[ColumnNames.MONTH].unique()[-2] if len(filtered_df[ColumnNames.MONTH].unique()) > 1 else None
    
    latest_data = filtered_df[filtered_df[ColumnNames.MONTH] == latest_month]
    previous_data = filtered_df[filtered_df[ColumnNames.MONTH] == previous_month] if previous_month else pd.DataFrame()
    
    # Calculate metrics
    metrics = calculate_metrics(latest_data, previous_data)
    
    # Render key metrics
    previous_month_exists = not previous_data.empty

    metrics_config = {
        'net_worth': {
            'label': 'Net Worth',
            'value': f"${metrics['current_net_worth']:,.0f}",
            'delta': f"{metrics['net_worth_pct_change']:+.2f}%" if previous_month_exists else None
        },
        'liabilities': {
            'label': 'Total Liabilities',
            'value': f"${metrics['current_liabilities']:,.0f}",
            'delta': f"{metrics['liabilities_change_pct']:+.2f}%" if previous_month_exists else None,
            'delta_color': 'inverse'
        },
        'debt_ratio': {
            'label': 'Debt Ratio',
            'value': f"{metrics['debt_ratio']:.1f}%"
        }
    }

    render_metric_cards(metrics_config, num_columns=3)
    
    st.divider()
    
    # category Breakdown
    st.subheader("category Breakdown")
    
    col_cat1, col_cat2 = st.columns(2)
    
    with col_cat1:
        st.markdown("**Holdings by category**")
        
        holdings_data = latest_data[latest_data[ColumnNames.ACCOUNT_TYPE] != 'Liability']
        holdings_by_category = holdings_data.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT].sum().sort_values(ascending=False)
        
        fig_holdings = create_horizontal_bar_chart(
            holdings_by_category, 
            "Holdings by category", 
            'assets',
            metrics['current_assets']
        )
        st.plotly_chart(fig_holdings, use_container_width=True)
    
    with col_cat2:
        st.markdown("**Liabilities by category**")
        
        liability_data = latest_data[latest_data[ColumnNames.ACCOUNT_TYPE] == 'Liability']
        
        if not liability_data.empty:
            liability_by_category = liability_data.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT].sum().abs().sort_values(ascending=False)
            
            fig_liabilities = create_horizontal_bar_chart(
                liability_by_category,
                "Liabilities by category",
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
        st.markdown("**account_type Distribution**")
        
        account_type_dist = latest_data.copy()
        account_type_dist['amount_Display'] = account_type_dist[ColumnNames.AMOUNT].abs()
        account_type_dist = account_type_dist.groupby(ColumnNames.ACCOUNT_TYPE)['amount_Display'].sum()
        
        fig_type = create_donut_chart(account_type_dist, "account_type Distribution")
        st.plotly_chart(fig_type, use_container_width=True)
    
    with col_pie2:
        st.markdown("**Top 5 accounts**")
        
        top_accounts = latest_data.copy()
        top_accounts[ColumnNames.AMOUNT] = top_accounts[ColumnNames.AMOUNT].abs()
        top_accounts = top_accounts.nlargest(5, ColumnNames.AMOUNT)[[ColumnNames.ACCOUNT, ColumnNames.AMOUNT, ColumnNames.CATEGORY]]
        
        fig_top = create_top_accounts_chart(top_accounts)
        st.plotly_chart(fig_top, use_container_width=True)
