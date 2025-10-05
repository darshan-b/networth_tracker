"""Overview tab for expense tracker.

Displays summary metrics, spending by category, and cumulative spending trends.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from data.calculations import calculate_expense_summary, calculate_category_spending
from ui.charts import create_donut_chart, create_line_chart
import streamlit.components.v1 as components
from constants import ColumnNames


# https://discuss.streamlit.io/t/changing-the-text-color-of-only-one-metric/35338/2
def color_widget_text(widget_text, color='#000000'):
    """
    Change the color of widget text in Streamlit using JavaScript injection.
    
    Args:
        widget_text: The text content to match
        color: Hex color code (default: black)
    
    Warning: This function injects user input into JavaScript. Ensure widget_text
    is from a trusted source to prevent XSS vulnerabilities.
    """
    html = f"""
    <script>
        var elements = window.parent.document.querySelectorAll('*');
        for (var i = 0; i < elements.length; i++) {{
            if (elements[i].innerText === '{widget_text}') {{
                elements[i].style.color = '{color}';
            }}
        }}
    </script>
    """
    
    # height = 0 or > 1 will keep adding horizontal lines
    components.html(html, height=1, width=0)


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
        st.metric("Total Spent", f"${summary['total_spent']:,.2f}", border=True, height='stretch')
        color_widget_text(f"${summary['total_spent']:,.2f}") 
    
    with col2:
        st.metric("Total Budget", f"${summary['total_budget']:,.2f}", border=True, height='stretch')
        color_widget_text(f"${summary['total_budget']:,.2f}") 
    
    with col3:
        remaining = summary['remaining']
        budget = summary['total_budget']
        color = "red" if remaining < 0 else "green"      
        remaining_pct = (remaining / budget * 100) if budget > 0 else 0
        st.metric("Remaining", f"${remaining:,.2f}", delta=f"{remaining_pct:.1f}%", border=True)
        if remaining < 0:
            color_widget_text(f"${remaining:,.2f}", '#FF0000') 
        else:
            color_widget_text(f"${remaining:,.2f}", '#00B050') 
    
    with col4:
        st.metric("Transactions", summary['num_transactions'], border=True, height='stretch')
        color_widget_text(str(summary['num_transactions'])) 


def _render_category_pie_chart(df):
    """
    Render a pie chart showing spending distribution by category.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Spending by category")
    
    try:
        category_spending = calculate_category_spending(df)
        
        if category_spending.empty:
            st.info("No category data available.")
            return
        
        fig = create_donut_chart(category_spending, '')
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
    Render filter controls for the spending trend chart with cascading filters.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
        
    Returns:
        pd.DataFrame: Filtered dataframe based on user selections
    """
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    # Category filter
    with col_filter1:
        categories = ['All'] + sorted(df[ColumnNames.CATEGORY].unique().tolist())
        selected_category = st.selectbox(
            'Category', 
            categories, 
            key='trend_cat'
        )
    
    # Filter dataframe for subcategory options
    df_for_subcat = df.copy()
    if selected_category != 'All':
        df_for_subcat = df_for_subcat[df_for_subcat[ColumnNames.CATEGORY] == selected_category]
    
    # Subcategory filter (cascading from category)
    with col_filter2:
        subcategories = ['All'] + sorted(df_for_subcat[ColumnNames.SUBCATEGORY].unique().tolist())
        selected_subcategory = st.selectbox(
            'Subcategory', 
            subcategories, 
            key='trend_subcat'
        )
    
    # Filter dataframe for merchant options
    df_for_merchant = df_for_subcat.copy()
    if selected_subcategory != 'All':
        df_for_merchant = df_for_merchant[df_for_merchant[ColumnNames.SUBCATEGORY] == selected_subcategory]
    
    # Merchant filter (cascading from category and subcategory)
    with col_filter3:
        merchants = ['All'] + sorted(df_for_merchant[ColumnNames.MERCHANT].unique().tolist())
        selected_merchant = st.selectbox(
            'Merchant', 
            merchants, 
            key='trend_merch'
        )
    
    # Apply filters to get final filtered dataframe
    filtered_df = df.copy()
    
    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df[ColumnNames.CATEGORY] == selected_category]
    
    if selected_subcategory != 'All':
        filtered_df = filtered_df[filtered_df[ColumnNames.SUBCATEGORY] == selected_subcategory]
    
    if selected_merchant != 'All':
        filtered_df = filtered_df[filtered_df[ColumnNames.MERCHANT] == selected_merchant]
    
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
        df.groupby(ColumnNames.DATE, as_index=False)[ColumnNames.AMOUNT]
        .sum()
        .sort_values(ColumnNames.DATE)
    )
    
    # Convert to positive values and calculate cumulative spending
    daily_spending[ColumnNames.AMOUNT] = daily_spending[ColumnNames.AMOUNT].abs()
    daily_spending['cumulative_amount'] = daily_spending[ColumnNames.AMOUNT].cumsum()
    
    return daily_spending


def _create_trend_chart(daily_spending):
    """
    Create a line chart for cumulative spending trend.
    
    Args:
        daily_spending (pd.DataFrame): Daily spending data with cumulative amounts
        
    Returns:
        plotly.graph_objects.Figure: Configured line chart
    """
    return create_line_chart(daily_spending, 
                            x=ColumnNames.DATE, 
                            y='cumulative_amount', 
                            x_title='Date', 
                            y_title="Cumulative Spending ($)")
