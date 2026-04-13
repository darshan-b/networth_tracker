"""Budgets tab for expense tracker.

Displays budget vs actual spending comparison and detailed budget progress tracking.
"""

import streamlit as st
import plotly.graph_objects as go
from data.calculations import calculate_budget_comparison
from app_constants import ColumnNames
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_metric_card,
    render_page_hero,
    render_section_intro,
)


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
    inject_surface_styles()
    render_page_hero(
        "Expenses",
        "Budgets",
        "Compare planned spend with actual spend and review category-level budget pressure.",
        "Use this tab to see where spending is tracking well and where it is running hot.",
    )
    
    if df.empty:
        st.info("No expense data available for the selected period.")
    
    try:
        budget_df = calculate_budget_comparison(df, budgets, num_months)

        render_section_intro(
            "Budget Health",
            "Start with the period context and overall budget status, then narrow the categories in focus.",
        )
        _render_period_info(num_months)
        render_section_intro(
            "Snapshot",
            "Quickly see how many categories are over budget, near the limit, or still on track.",
        )
        _render_budget_summary_cards(budget_df)

        render_section_intro(
            "Controls",
            "Focus the chart and detail cards on the categories that matter most right now.",
        )
        budget_df = _apply_budget_filters(budget_df)

        render_section_intro(
            "Budget vs Actual",
            "Compare planned spend with actual spend across the categories currently in focus.",
        )
        _render_budget_comparison_chart(budget_df)
    except Exception as e:
        st.error(f"Error calculating budget comparison: {str(e)}")
        return
    
    st.divider()
    
    render_section_intro(
        "Category Detail",
        "Review each category budget card for remaining room or overages.",
    )
    _render_budget_details(budgets, budget_df, num_months)
    
    st.caption("Budgets are read-only in the app. Update the source budget file to make changes.")


def _render_period_info(num_months):
    """
    Display information about the budget period.
    
    Args:
        num_months (int): Number of months in the selected period
    """
    render_accent_pills(
        [
            ("Budget Window", f"{num_months} month{'s' if num_months != 1 else ''}"),
        ]
    )


def _render_budget_comparison_chart(budget_df):
    """
    Render a grouped bar chart comparing budgets vs actual spending.
    
    Args:
        budget_df (pd.DataFrame): Budget comparison dataframe
    """
    st.markdown("#### Budget vs Actual")
    
    if budget_df.empty:
        st.info("No budget data available.")
        return
    
    try:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Budget', 
            x=budget_df[ColumnNames.CATEGORY], 
            y=budget_df['Budget'], 
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='Spent', 
            x=budget_df[ColumnNames.CATEGORY], 
            y=budget_df['Spent'],
            marker_color='coral'
        ))
        
        fig.update_layout(
            barmode='group', 
            xaxis_title="", 
            yaxis_title="amount ($)",
            hovermode="x unified",
        )
        fig.update_traces(marker_line_width=0, marker_line_color="rgba(0,0,0,0)", marker=dict(cornerradius=10))
        
        st.plotly_chart(fig, config={"responsive": True})
        
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
    st.markdown("#### Category Budgets")
    
    col1, col2 = st.columns(2)
    
    budget_lookup = {row[ColumnNames.CATEGORY]: row for _, row in budget_df.iterrows()}
    ordered_categories = [
        category for category in budget_df[ColumnNames.CATEGORY].tolist()
        if category in budgets
    ]

    for idx, category in enumerate(ordered_categories):
        monthly_budget = budgets[category]
        with col1 if idx % 2 == 0 else col2:
            _render_budget_card(category, monthly_budget, budget_lookup, num_months)


def _render_budget_card(category, monthly_budget, budget_lookup, num_months):
    """
    Render a single budget tracking card for a category.
    
    Args:
        category (str): Budget category name
        monthly_budget (float): monthly budget amount
        budget_df (pd.DataFrame): Budget comparison dataframe
        num_months (int): Number of months in the selected period
    """
    # Get budget data for this category
    row = budget_lookup.get(category)

    if row is not None:
        spent = row['Spent']
        scaled_budget = row['Budget']
        percentage = row['Percentage']
        remaining = row['Remaining']
    else:
        spent = 0
        scaled_budget = monthly_budget * num_months
        percentage = 0
        remaining = scaled_budget
    
    st.write(f"**{category}**")
    
    # Display budget metrics
    if num_months > 1:
        st.metric(
            f"Budget ({num_months} months)", 
            f"${scaled_budget:,.2f}",
            delta=f"${spent:,.2f} spent"
        )
        st.caption(f"Monthly budget: ${monthly_budget:,.2f} | Remaining: ${remaining:,.2f}")
    else:
        st.metric(
            "Budget", 
            f"${monthly_budget:,.2f}", 
            delta=f"${spent:,.2f} spent"
        )
        st.caption(f"Remaining: ${remaining:,.2f}")
    
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


def _render_budget_summary_cards(budget_df):
    """Render quick budget health metrics from the current comparison data."""
    over_budget = int((budget_df["Percentage"] > 100).sum())
    near_limit = int(((budget_df["Percentage"] > 80) & (budget_df["Percentage"] <= 100)).sum())
    on_track = int((budget_df["Percentage"] <= 80).sum())
    total_remaining = float(budget_df["Remaining"].sum())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Over Budget", str(over_budget), "Categories", "Categories already above budget.", "negative" if over_budget else "neutral")
    with col2:
        render_metric_card("Near Limit", str(near_limit), "Categories", "Categories above 80% but not yet over.", "neutral")
    with col3:
        render_metric_card("On Track", str(on_track), "Categories", "Categories still comfortably within plan.", "positive")
    with col4:
        render_metric_card("Net Remaining", f"${total_remaining:,.0f}", "Across budgets", "Total budget left after current spending.", "positive" if total_remaining >= 0 else "negative")
    render_accent_pills(
        [
            ("Tracked Categories", str(len(budget_df))),
            ("Highest Pressure", f"{budget_df['Percentage'].max():.0f}%" if not budget_df.empty else "0%"),
        ]
    )


def _apply_budget_filters(budget_df):
    """Filter and sort the budget comparison for more useful review."""
    col1, col2 = st.columns([1.2, 1.2])
    with col1:
        status_filter = st.multiselect(
            "Status",
            options=["Over Budget", "Near Limit", "On Track"],
            default=["Over Budget", "Near Limit", "On Track"],
            help="Filter categories by budget health status.",
        )
    with col2:
        sort_by = st.selectbox(
            "Sort By",
            options=["Budget Pressure", "Largest Overspend", "Largest Remaining", "Alphabetical"],
            index=0,
        )

    working_df = budget_df.copy()
    working_df["Status"] = "On Track"
    working_df.loc[(working_df["Percentage"] > 80) & (working_df["Percentage"] <= 100), "Status"] = "Near Limit"
    working_df.loc[working_df["Percentage"] > 100, "Status"] = "Over Budget"

    if status_filter:
        working_df = working_df[working_df["Status"].isin(status_filter)]

    if sort_by == "Budget Pressure":
        working_df = working_df.sort_values("Percentage", ascending=False)
    elif sort_by == "Largest Overspend":
        working_df = working_df.sort_values("Remaining")
    elif sort_by == "Largest Remaining":
        working_df = working_df.sort_values("Remaining", ascending=False)
    else:
        working_df = working_df.sort_values(ColumnNames.CATEGORY)

    return working_df.reset_index(drop=True)

