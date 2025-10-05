"""Budgets tab for expense tracker.

Displays budget vs actual spending comparison and detailed budget progress tracking.
"""

import streamlit as st
import plotly.graph_objects as go
from data.calculations import calculate_budget_comparison


def render_budgets_tab(df, budgets, num_months=1):
    """
    Render the budget management tab with comparison charts and progress tracking.
    
    Args:
        df (pd.DataFrame): Transactions dataframe filtered for expenses only
        budgets (dict): Dictionary of monthly budgets by category
        num_months (int): Number of distinct months in the selected date range
        
    Returns:
        None
    """
    st.subheader("Budget Management")
    
    if df.empty:
        st.info("No expense data available for the selected period.")
    
    # Display budget period information
    _render_period_info(num_months)
    
    # Calculate and display budget comparison
    try:
        budget_df = calculate_budget_comparison(df, budgets, num_months)
        _render_budget_comparison_chart(budget_df)
    except Exception as e:
        st.error(f"Error calculating budget comparison: {str(e)}")
        return
    
    st.divider()
    
    # Display detailed budget tracking
    _render_budget_details(budgets, budget_df, num_months)
    
    # Display informational message
    st.info(
        "Read-only mode: To modify budgets, edit your budgets.xlsx/csv file "
        "and reload the app."
    )


def _render_period_info(num_months):
    """
    Display information about the budget period.
    
    Args:
        num_months (int): Number of months in the selected period
    """
    if num_months == 1:
        period_info = "Budget for 1 month"
    else:
        period_info = f"Budget for {num_months} months"
    
    st.info(period_info)


def _render_budget_comparison_chart(budget_df):
    """
    Render a grouped bar chart comparing budgets vs actual spending.
    
    Args:
        budget_df (pd.DataFrame): Budget comparison dataframe
    """
    st.markdown("#### Budget vs Actual (Selected Period)")
    
    if budget_df.empty:
        st.info("No budget data available.")
        return
    
    try:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Budget', 
            x=budget_df['category'], 
            y=budget_df['Budget'], 
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Spent', 
            x=budget_df['category'], 
            y=budget_df['Spent'],
            marker_color='coral'
        ))
        
        fig.update_layout(
            barmode='group', 
            xaxis_title="", 
            yaxis_title="amount ($)"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error rendering budget comparison chart: {str(e)}")


def _render_budget_details(budgets, budget_df, num_months):
    """
    Render detailed budget tracking cards for each category.
    
    Args:
        budgets (dict): Dictionary of monthly budgets by category
        budget_df (pd.DataFrame): Budget comparison dataframe
        num_months (int): Number of months in the selected period
    """
    st.markdown("#### monthly Budgets")
    
    col1, col2 = st.columns(2)
    
    for idx, (category, monthly_budget) in enumerate(budgets.items()):
        with col1 if idx % 2 == 0 else col2:
            _render_budget_card(category, monthly_budget, budget_df, num_months)


def _render_budget_card(category, monthly_budget, budget_df, num_months):
    """
    Render a single budget tracking card for a category.
    
    Args:
        category (str): Budget category name
        monthly_budget (float): monthly budget amount
        budget_df (pd.DataFrame): Budget comparison dataframe
        num_months (int): Number of months in the selected period
    """
    # Get budget data for this category
    category_data = budget_df[budget_df['category'] == category]
    
    if not category_data.empty:
        row = category_data.iloc[0]
        spent = row['Spent']
        scaled_budget = row['Budget']
        percentage = row['Percentage']
    else:
        spent = 0
        scaled_budget = monthly_budget * num_months
        percentage = 0
    
    st.write(f"**{category}**")
    
    # Display budget metrics
    if num_months > 1:
        st.metric(
            f"Budget ({num_months} months)", 
            f"${scaled_budget:,.2f}",
            delta=f"${spent:,.2f} spent"
        )
        st.caption(f"monthly budget: ${monthly_budget:,.2f}")
    else:
        st.metric(
            "Budget", 
            f"${monthly_budget:,.2f}", 
            delta=f"${spent:,.2f} spent"
        )
    
    # Render progress bar
    _render_budget_progress(spent, scaled_budget, percentage)
    
    st.divider()


def _render_budget_progress(spent, budget, percentage):
    """
    Render progress bar and status message for budget tracking.
    
    Args:
        spent (float): amount spent
        budget (float): Budget amount
        percentage (float): Percentage of budget spent
    """
    # Progress bar (clamp between 0 and 1)
    progress_value = max(0.0, min(1.0, percentage / 100))
    st.progress(progress_value)
    
    # Color-coded status message
    remaining = budget - spent
    
    if percentage > 100:
        st.error(
            f"Over budget by ${spent - budget:,.2f} ({percentage:.1f}%)"
        )
    elif percentage > 80:
        st.warning(
            f"${remaining:,.2f} remaining ({100 - percentage:.1f}%)"
        )
    else:
        st.success(
            f"${remaining:,.2f} remaining ({100 - percentage:.1f}%)"
        )