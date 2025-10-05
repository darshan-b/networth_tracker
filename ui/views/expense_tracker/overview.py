"""Overview tab for expense tracker.

Displays summary metrics, spending by category, and cumulative spending trends.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from data.calculations import calculate_expense_summary, calculate_category_spending


def render_overview_tab(df, budgets, num_months=1):
    """
    Render the expense overview tab with summary metrics and visualizations.
    
    Args:
        df (pd.DataFrame): Transactions dataframe filtered for expenses only
        budgets (dict): Dictionary of monthly budgets by category
        num_months (int): Number of distinct months in the selected date range
        
    Returns:
        None
    """
    st.subheader("Expense Overview")
    
    if df.empty:
        st.info("No expense data available for the selected period.")
        return
    
    # Calculate summary metrics
    try:
        summary = calculate_expense_summary(df, budgets, num_months)
    except Exception as e:
        st.error(f"Error calculating expense summary: {str(e)}")
        return
    
    # Display key metrics
    _render_summary_metrics(summary)
    
    st.divider()
    
    # Display charts
    col1, col2 = st.columns(2)
    
    with col1:
        _render_category_pie_chart(df)
    
    with col2:
        _render_spending_trend_chart(df)


def _render_summary_metrics(summary):
    """
    Display summary metrics in a four-column layout.
    
    Args:
        summary (dict): Dictionary containing summary statistics
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Spent", f"${summary['total_spent']:,.2f}")
    
    with col2:
        st.metric("Total Budget", f"${summary['total_budget']:,.2f}")
    
    with col3:
        remaining = summary['remaining']
        budget = summary['total_budget']
        remaining_pct = (remaining / budget * 100) if budget > 0 else 0
        st.metric(
            "Remaining", 
            f"${remaining:,.2f}", 
            delta=f"{remaining_pct:.1f}%"
        )
    
    with col4:
        st.metric("Transactions", summary['num_transactions'])


def _render_category_pie_chart(df):
    """
    Render a pie chart showing spending distribution by category.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Spending by Category")
    
    try:
        category_spending = calculate_category_spending(df)
        
        if category_spending.empty:
            st.info("No category data available.")
            return
        
        fig = px.pie(
            category_spending, 
            values='amount', 
            names='category',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering category chart: {str(e)}")


def _render_spending_trend_chart(df):
    """
    Render a line chart showing cumulative spending over time with filters.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Spending Trend")
    
    # Render filter controls
    filtered_df = _render_trend_filters(df)
    
    if filtered_df.empty:
        st.info("No data available for selected filters.")
        return
    
    # Aggregate and plot data
    try:
        daily_spending = _aggregate_daily_spending(filtered_df)
        fig = _create_trend_chart(daily_spending)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error rendering spending trend: {str(e)}")


def _render_trend_filters(df):
    """
    Render filter controls for the spending trend chart.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
        
    Returns:
        pd.DataFrame: Filtered dataframe based on user selections
    """
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        categories = ['All'] + sorted(df['category'].unique().tolist())
        selected_category = st.selectbox(
            'Category', 
            categories, 
            key='trend_cat'
        )
    
    with col_filter2:
        subcategories = ['All'] + sorted(df['subcategory'].unique().tolist())
        selected_subcategory = st.selectbox(
            'Subcategory', 
            subcategories, 
            key='trend_subcat'
        )
    
    with col_filter3:
        merchants = ['All'] + sorted(df['merchant'].unique().tolist())
        selected_merchant = st.selectbox(
            'Merchant', 
            merchants, 
            key='trend_merch'
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    if selected_subcategory != 'All':
        filtered_df = filtered_df[filtered_df['subcategory'] == selected_subcategory]
    
    if selected_merchant != 'All':
        filtered_df = filtered_df[filtered_df['merchant'] == selected_merchant]
    
    return filtered_df


def _aggregate_daily_spending(df):
    """
    Aggregate spending by day and calculate cumulative totals.
    
    Args:
        df (pd.DataFrame): Filtered transactions dataframe
        
    Returns:
        pd.DataFrame: Daily spending with cumulative amounts
    """
    daily_spending = (
        df.groupby('date', as_index=False)['amount']
        .sum()
        .sort_values('date')
    )
    
    # Convert to positive values and calculate cumulative spending
    daily_spending['amount'] = daily_spending['amount'].abs()
    daily_spending['cumulative_amount'] = daily_spending['amount'].cumsum()
    
    return daily_spending


def _create_trend_chart(daily_spending):
    """
    Create a line chart for cumulative spending trend.
    
    Args:
        daily_spending (pd.DataFrame): Daily spending data with cumulative amounts
        
    Returns:
        plotly.graph_objects.Figure: Configured line chart
    """
    fig = px.line(
        daily_spending, 
        x='date', 
        y='cumulative_amount',
        markers=True
    )
    
    fig.update_traces(
        line_color='#1f77b4',
        line_width=3,
        marker=dict(size=8),
        mode='lines'
    )
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative Spending ($)",
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='lightgray'),
        xaxis=dict(showgrid=False)
    )
    
    return fig
