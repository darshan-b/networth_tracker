"""Insights tab for expense tracker.

Provides analytical insights including top merchants, spending patterns, and trends.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.calculations import (
    calculate_top_merchants,
    calculate_spending_by_dow,
    calculate_category_trends,
    _convert_to_absolute
)
from constants import ColumnNames
import plotly.io as pio
pio.templates.default = 'plotly_dark' 



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
    
    col1, col2 = st.columns([0.6, 0.4], border=True)
    with col1:
        # Top merchants analysis
        _render_top_merchants(df[df[ColumnNames.CATEGORY]!='Income'])

    with col2:
        # Summary statistics
        _render_summary_statistics(df[df[ColumnNames.CATEGORY]!='Income'])

    st.divider()
    
    # Spending patterns
    col1, col2 = st.columns(2)
    
    with col1:
        _render_dow_spending(df[df[ColumnNames.CATEGORY]!='Income'])
    
    with col2:
        _render_avg_transaction_by_category(df[df[ColumnNames.CATEGORY]!='Income'])
    

    
    st.divider()
    
    # category trends over time
    _render_category_trends(df[df[ColumnNames.CATEGORY]!='Income'])

    _render_cash_flow(df)


def _render_top_merchants(df):
    """
    Render horizontal bar chart of top merchants by spending.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("<h3 style='text-align: center;'>Expenses Breakdown</h3>", unsafe_allow_html=True)
    
    try:
        # Prepare data for all charts first
        top_merchants = calculate_top_merchants(df, limit=10)
        top_categories = df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT].sum().apply(_convert_to_absolute).sort_values(ascending=False).head(10).reset_index()
        top_subcategories = df.groupby(ColumnNames.SUBCATEGORY)[ColumnNames.AMOUNT].sum().apply(_convert_to_absolute).sort_values(ascending=False).head(10).reset_index()

        # Pill buttons for selection
        col1, col2 = st.columns([0.33, 0.67])
        with col2:
            selected = st.pills(
                "View",
                ["By Merchant", "By Category", "By Subcategory"],
                label_visibility="collapsed"
            )

        # Display based on selection
        with st.container(border=True):
            if selected == "By Merchant":
                st.subheader("By Merchant")
                
                fig = px.bar(
                    top_merchants,
                    x=ColumnNames.AMOUNT,
                    y=ColumnNames.MERCHANT,
                    orientation='h',
                    color=ColumnNames.MERCHANT,
                    text=ColumnNames.AMOUNT
                )
                fig.update_traces(texttemplate='$%{text:,.0f}', textposition='auto')
                fig.update_layout(
                    showlegend=False,
                    xaxis_title="Amount ($)",
                    yaxis_title="",
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            elif selected == "By Category":
                st.subheader("By Category")
                
                fig = px.bar(
                    top_categories,
                    x=ColumnNames.AMOUNT,
                    y=ColumnNames.CATEGORY,
                    orientation='h',
                    color=ColumnNames.CATEGORY,
                    text=ColumnNames.AMOUNT
                )
                fig.update_traces(texttemplate='$%{text:,.0f}', textposition='auto')
                fig.update_layout(
                    showlegend=False,
                    xaxis_title="Amount ($)",
                    yaxis_title="",
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
            else:  # By Subcategory
                st.subheader("By Subcategory")
                
                fig = px.bar(
                    top_subcategories,
                    x=ColumnNames.AMOUNT,
                    y=ColumnNames.SUBCATEGORY,
                    orientation='h',
                    color=ColumnNames.SUBCATEGORY,
                    text=ColumnNames.AMOUNT
                )
                fig.update_traces(texttemplate='$%{text:,.0f}', textposition='auto')
                fig.update_layout(
                    showlegend=False,
                    xaxis_title="Amount ($)",
                    yaxis_title="",
                     yaxis={'categoryorder': 'total ascending'}
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
            y=ColumnNames.AMOUNT,
            color=ColumnNames.AMOUNT,
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
    st.markdown("#### Average Transaction by Category")
    
    try:
        avg_by_category = (
            df.groupby(ColumnNames.DATE)[ColumnNames.AMOUNT]
            .apply(lambda x: abs(x.mean()))
            .sort_values(ascending=False)
            .reset_index()
        )
        
        if avg_by_category.empty:
            st.info("No category data available.")
            return
        
        fig = px.bar(
            avg_by_category, 
            x=ColumnNames.DATE, 
            y=ColumnNames.AMOUNT,
            color=ColumnNames.AMOUNT,
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
    st.header("Summary", divider=True)

    # Calculate some reusable values
    total_amount = abs(df[ColumnNames.AMOUNT].sum())
    days_in_period = (df[ColumnNames.DATE].max() - df[ColumnNames.DATE].min()).days + 1

    # Row 1: Core spending metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.metric("Total Spend", f"${total_amount:,.2f}")

    with col2:
        with st.container(border=True):
            avg_amount = abs(df[ColumnNames.AMOUNT].mean())
            st.metric("Average Transaction", f"${avg_amount:.2f}")

    with col3:
        with st.container(border=True):
            median_amount = abs(df[ColumnNames.AMOUNT].median())
            st.metric("Median Transaction", f"${median_amount:.2f}")

    # Row 2: Transaction counts and daily average
    col4, col5 = st.columns(2)
    with col4:
        with st.container(border=True):
            largest_amount = abs(df[ColumnNames.AMOUNT].min())
            st.metric("Largest Transaction", f"${largest_amount:.2f}")
            if not df.empty:
                try:
                    largest = df.loc[df[ColumnNames.AMOUNT].idxmin()]
                    st.caption(f"{largest[ColumnNames.MERCHANT]} - {largest[ColumnNames.CATEGORY]}")
                except Exception:
                    pass

    with col5:
        with st.container(border=True):
            daily_totals = df.groupby(df[ColumnNames.DATE].dt.date)[ColumnNames.AMOUNT].sum().abs()
            most_expensive_day = daily_totals.idxmax()
            most_expensive_amount = daily_totals.max()
            st.metric("Most Expensive Day", most_expensive_day.strftime("%b %d, %Y"))
            st.caption(f"${most_expensive_amount:,.2f}")

    # Row 4: Category insights
    col6, col7 = st.columns(2)
    with col6:
        with st.container(border=True):
            if not df.empty:
                try:
                    most_frequent_merchant = df[ColumnNames.MERCHANT].mode()[0]
                    st.metric("Most Frequent Merchant", most_frequent_merchant)
                except Exception:
                    st.info("Insufficient data")

    with col7:
        with st.container(border=True):
            if not df.empty:
                try:
                    most_frequent_category = df[ColumnNames.CATEGORY].mode()[0]
                    st.metric("Most Frequent Category", most_frequent_category)
                except Exception:
                    st.info("Insufficient data")

    col8, col9 = st.columns(2)
    with col8:
        # Row 8: Month-over-month change (if applicable)
        if df[ColumnNames.DATE].dt.month.nunique() > 1:
            with st.container(border=True):
                current_month_num = df[ColumnNames.DATE].dt.month.max()
                current_month = df[df[ColumnNames.DATE].dt.month == current_month_num]
                prev_month = df[df[ColumnNames.DATE].dt.month == current_month_num - 1]
                
                if not prev_month.empty:
                    current_total = abs(current_month[ColumnNames.AMOUNT].sum())
                    prev_total = abs(prev_month[ColumnNames.AMOUNT].sum())
                    change = current_total - prev_total
                    change_pct = (change / prev_total * 100) if prev_total > 0 else 0
                    
                    st.metric("Current Month Spending", f"${current_total:,.2f}",
                            delta=f"{change_pct:+.1f}% vs previous month", 
                            delta_color="inverse")

    with col9:
        with st.container(border=True):
            top_category = df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT].sum().abs().idxmax()
            top_category_amount = df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT].sum().abs().max()
            percentage = (top_category_amount / total_amount) * 100
            st.metric("Top Spending Category", top_category)
            st.caption(f"{percentage:.1f}% of total (${top_category_amount:,.2f})")

def _render_category_trends(df):
    """
    Render line chart showing category spending trends over time.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Category Spending Over Time")
    
    try:
        category_monthly = calculate_category_trends(df)
        
        if category_monthly.empty:
            st.info("Insufficient data for trend analysis.")
            return
        
        fig = px.line(
            category_monthly, 
            x=ColumnNames.MONTH, 
            y=ColumnNames.AMOUNT, 
            color=ColumnNames.CATEGORY,
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


def _render_cash_flow(df):

    
    st.markdown("<h3 style='text-align: center;'>Cash Flow by Month</h3>", unsafe_allow_html=True)

    # Create figure
    fig = go.Figure()

    df['month'] = df[ColumnNames.DATE].dt.to_period('M').astype(str)
    df = df[df[ColumnNames.SUBCATEGORY]!='Transfer']
    income = df[df[ColumnNames.CATEGORY]=='Income']
    income = income.groupby(['month'])[ColumnNames.AMOUNT].sum()

    expense = df[df[ColumnNames.CATEGORY]!='Income']
    expense = expense.groupby(['month'])[ColumnNames.AMOUNT].sum()

    savings = df.groupby(['month'])[ColumnNames.AMOUNT].sum()

    # Add positive bars (green)
    fig.add_trace(go.Bar(
        x=income.index,
        y=income.values,
        marker_color='rgba(144, 238, 144, 0.9)',
        hovertemplate='Income: %{y:$,.0f}<extra></extra>',
        name='Income'
    ))

    # Add negative bars (red/pink)
    fig.add_trace(go.Bar(
        x=expense.index,
        y=expense.values,
        marker_color='rgba(255, 182, 193, 0.9)',
        hovertemplate='Expenses: %{y:$,.0f}<extra></extra>',
        name='Expenses'
    ))

    # Add solid line for savings
    fig.add_trace(go.Scatter(
        x=savings.index, 
        y=savings.values,
        mode='lines+markers',
        name='Savings',
        line=dict(color='blue', width=2),
        hovertemplate='Savings: %{y:$,.0f}<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        barmode='relative',  # Stack bars
        height=400,
        margin=dict(l=50, r=50, t=50, b=50),
        # plot_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linecolor='lightgray'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            showline=True,
            linecolor='lightgray',
            tickformat='$,.0f',
            tickprefix='',
            zeroline=True,
            zerolinecolor='lightgray'
        ),
        hovermode='x unified',
        showlegend=False,
        template = 'plotly_dark'
    )
    container = st.container(border=True)  # Simple built-in border

    with container:
        st.plotly_chart(fig, use_container_width=True)