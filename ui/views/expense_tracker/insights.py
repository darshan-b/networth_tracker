"""Insights tab for expense tracker.

Provides analytical insights including top merchants, spending patterns, and trends.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from data.calculations import (
    calculate_top_merchants,
    calculate_spending_by_dow,
    calculate_category_trends
)


def render_insights_tab(df):
    """
    Render the financial insights tab with various analytical visualizations.
    
    Args:
        df (pd.DataFrame): Transactions dataframe filtered for expenses only
        
    Returns:
        None
    """
    st.subheader("Financial Insights")
    
    if df.empty:
        st.info("No expense data available for the selected period.")
        return
    
    # Top merchants analysis
    _render_top_merchants(df)
    
    st.divider()
    
    # Spending patterns
    col1, col2 = st.columns(2)
    
    with col1:
        _render_dow_spending(df)
    
    with col2:
        _render_avg_transaction_by_category(df)
    
    st.divider()
    
    # Summary statistics
    _render_summary_statistics(df)
    
    st.divider()
    
    # category trends over time
    _render_category_trends(df)


def _render_top_merchants(df):
    """
    Render horizontal bar chart of top merchants by spending.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Top Merchants")
    
    try:
        top_merchants = calculate_top_merchants(df, limit=10)
        
        if top_merchants.empty:
            st.info("No merchant data available.")
            return
        
        fig = px.bar(
            top_merchants, 
            x='amount', 
            y='merchant', 
            orientation='h',
            color='amount',
            color_continuous_scale='Reds'
        )
        fig.update_layout(
            showlegend=False, 
            xaxis_title="amount ($)", 
            yaxis_title=""
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering top merchants: {str(e)}")


def _render_dow_spending(df):
    """
    Render bar chart of spending by day of week.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Spending by Day of Week")
    
    try:
        dow_spending = calculate_spending_by_dow(df)
        
        if dow_spending.empty:
            st.info("No day-of-week data available.")
            return
        
        fig = px.bar(
            dow_spending, 
            x='day_of_week', 
            y='amount',
            color='amount',
            color_continuous_scale='Greens'
        )
        fig.update_layout(
            showlegend=False, 
            xaxis_title="", 
            yaxis_title="amount ($)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering day-of-week spending: {str(e)}")


def _render_avg_transaction_by_category(df):
    """
    Render bar chart of average transaction amount by category.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Average Transaction by category")
    
    try:
        avg_by_category = (
            df.groupby('category')['amount']
            .apply(lambda x: abs(x.mean()))
            .sort_values(ascending=False)
            .reset_index()
        )
        
        if avg_by_category.empty:
            st.info("No category data available.")
            return
        
        fig = px.bar(
            avg_by_category, 
            x='category', 
            y='amount',
            color='amount',
            color_continuous_scale='Purples'
        )
        fig.update_layout(
            showlegend=False, 
            xaxis_title="", 
            yaxis_title="Average ($)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering average transactions: {str(e)}")


def _render_summary_statistics(df):
    """
    Display summary statistics in a three-column layout.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Transactions", len(df))
        avg_amount = abs(df['amount'].mean())
        st.metric("Average Transaction", f"${avg_amount:.2f}")
    
    with col2:
        largest_amount = abs(df['amount'].min())
        st.metric("Largest Transaction", f"${largest_amount:.2f}")
        
        if not df.empty:
            try:
                largest = df.loc[df['amount'].idxmin()]
                st.caption(f"{largest['merchant']} - {largest['category']}")
            except Exception:
                pass
    
    with col3:
        if not df.empty:
            try:
                most_frequent_merchant = df['merchant'].mode()[0]
                st.metric("Most Frequent Merchant", most_frequent_merchant)
                
                most_frequent_category = df['category'].mode()[0]
                st.metric("Most Frequent category", most_frequent_category)
            except Exception:
                st.info("Insufficient data for frequency analysis.")


def _render_category_trends(df):
    """
    Render line chart showing category spending trends over time.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### category Spending Over Time")
    
    try:
        category_monthly = calculate_category_trends(df)
        
        if category_monthly.empty:
            st.info("Insufficient data for trend analysis.")
            return
        
        fig = px.line(
            category_monthly, 
            x='month', 
            y='amount', 
            color='category',
            markers=True
        )
        fig.update_layout(
            xaxis_title="month", 
            yaxis_title="amount ($)",
            xaxis=dict(tickformat="%b %Y")
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering category trends: {str(e)}")