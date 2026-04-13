"""Overview tab for expense tracker."""

import streamlit as st
import pandas as pd
from data.calculations import (
    calculate_category_spending,
    calculate_expense_summary,
    is_income_transaction,
    is_refund_transaction,
)
from ui.charts import create_donut_chart, create_line_chart, create_bar_chart
from app_constants import ColumnNames
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_metric_card,
    render_page_hero,
    render_section_intro,
)


def render_overview_tab(df, budgets, num_months=1, period_start=None, period_end=None):
    """
    Render the expense overview tab with summary metrics and visualizations.
    
    Args:
        df (pd.DataFrame): Transactions dataframe filtered for expenses only
        budgets (dict): Dictionary of monthly budgets by category
        num_months (int): Number of distinct months in the selected date range
        period_start: Selected period start date
        period_end: Selected period end date
        
    Returns:
        None
    """
    inject_surface_styles()
    render_page_hero(
        "Expenses",
        "Overview",
        "Review spending, income, savings, and category mix for the selected period.",
        "Start here for the top-line picture before drilling into budgets, transactions, or insights.",
    )
    
    if df.empty:
        st.info("No expense data available for the selected period.")
        return
    
    # Calculate summary metrics
    try:
        summary = calculate_expense_summary(df, budgets, num_months)
    except Exception as e:
        st.error(f"Error calculating expense summary: {str(e)}")
        return
    
    render_section_intro("Snapshot", "A quick read on spending, income, savings, and remaining budget.")
    _render_summary_metrics(summary, num_months)
    _render_overview_pills(df, summary)

    st.divider()
    render_section_intro("Spending View", "Use the mix, leaders, and trend together to see where spending concentrated and how it built up.")

    col1, col2 = st.columns([0.95, 1.05])
    with col1:
        _render_category_pie_chart(df)
        _render_top_category_snapshot(df)
    with col2:
        _render_spending_trend_chart(df, period_start, period_end)


def _render_summary_metrics(summary, num_months):
    """
    Display summary metrics in a four-column layout.
    
    Args:
        summary (dict): Dictionary containing summary statistics
    """
    col1, col2, col3= st.columns(3)
    
    with col1:
        render_metric_card(
            "Net Spending",
            f"${summary['total_spent']:,.0f}",
            "Selected period",
            "Net spend after refunds and credits reduce expense totals.",
            "negative",
        )
    with col2:
        render_metric_card(
            "Total Income",
            f"${summary['total_income']:,.0f}",
            "Selected period",
            "All income recorded in the active filter window.",
            "positive",
        )
    with col3:
        render_metric_card(
            "Total Savings",
            f"${summary['total_savings']:,.0f}",
            f"{summary['savings_rate']}%",
            "Net cash flow across the selected period.",
            "positive" if summary["total_savings"] > 0 else "negative" if summary["total_savings"] < 0 else "neutral",
        )
    col4, col5, _ = st.columns(3)

    with col4:
        render_metric_card(
            "Total Budget",
            f"${summary['total_budget']:,.0f}",
            f"{num_months} month{'s' if num_months != 1 else ''}",
            "Budget capacity for the selected period.",
            "neutral",
        )
    with col5:
        remaining = summary['remaining']
        budget = summary['total_budget']
        remaining_pct = (remaining / budget * 100) if budget > 0 else 0
        render_metric_card(
            "Remaining",
            f"${remaining:,.0f}",
            f"{remaining_pct:.1f}%",
            "Budget left after recorded spending.",
            "positive" if remaining > 0 else "negative" if remaining < 0 else "neutral",
        )
        

def _render_overview_pills(df: pd.DataFrame, summary: dict) -> None:
    """Render compact supporting context below the primary metric cards."""
    refund_count = int(is_refund_transaction(df).sum())
    active_merchants = df[ColumnNames.MERCHANT].nunique()
    categories = df[ColumnNames.CATEGORY].nunique()
    render_accent_pills(
        [
            ("Refunds/Credits", f"${summary.get('total_refunds', 0):,.0f}"),
            ("Gross Spend", f"${summary.get('gross_spent', summary['total_spent']):,.0f}"),
            ("Transactions", f"{len(df):,}"),
            ("Refund Rows", str(refund_count)),
            ("Merchants", str(active_merchants)),
            ("Categories", str(categories)),
        ]
    )


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
        
        fig = create_donut_chart(category_spending, '')
        st.plotly_chart(fig, config={"responsive": True})
        
    except Exception as e:
        st.error(f"Error rendering category chart: {str(e)}")


def _render_top_category_snapshot(df: pd.DataFrame) -> None:
    """Render a compact ranked category view beside the donut."""
    category_spending = calculate_category_spending(df).head(5)
    if category_spending.empty:
        return

    st.markdown("#### Biggest Categories")
    fig = create_bar_chart(
        category_spending.sort_values(),
        orientation="h",
        color_scheme="networth",
        show_values=True,
        x_label="Net spend ($)",
        height=300,
    )
    fig.update_layout(margin={"l": 24, "r": 16, "t": 24, "b": 24})
    st.plotly_chart(fig, config={"responsive": True})


def _render_spending_trend_chart(df, period_start=None, period_end=None):
    """
    Render a line chart showing cumulative spending over time with filters.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Spending Trend")
    st.caption("Refine the trend by category, subcategory, or merchant.")

    with st.expander("Trend Filters", expanded=False):
        filtered_df = _render_trend_filters(df)
    
    if filtered_df.empty:
        st.info("No data available for selected filters.")
        return
    
    # Aggregate and plot data
    try:
        daily_spending = _aggregate_daily_spending(filtered_df, period_start, period_end)
        fig = _create_trend_chart(daily_spending)
        st.plotly_chart(fig, config={"responsive": True})
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


def _aggregate_daily_spending(df, period_start=None, period_end=None):
    """
    Aggregate spending by day and calculate cumulative totals.
    
    Args:
        df (pd.DataFrame): Filtered transactions dataframe
        period_start: Selected period start date
        period_end: Selected period end date
        
    Returns:
        pd.DataFrame: Daily spending with cumulative amounts
    """
    non_income_df = df[~is_income_transaction(df)].copy()

    if period_start is None:
        period_start = df[ColumnNames.DATE].min()
    if period_end is None:
        period_end = df[ColumnNames.DATE].max()

    period_start = pd.to_datetime(period_start).normalize()
    period_end = pd.to_datetime(period_end).normalize()

    all_dates = pd.date_range(period_start, period_end, freq="D")

    if non_income_df.empty:
        daily_spending = pd.DataFrame(
            {
                ColumnNames.DATE: all_dates,
                ColumnNames.AMOUNT: 0.0,
            }
        )
    else:
        daily_spending = (
            non_income_df.groupby(ColumnNames.DATE)[ColumnNames.AMOUNT]
            .sum()
            .reindex(all_dates, fill_value=0.0)
            .rename_axis(ColumnNames.DATE)
            .reset_index()
            .sort_values(ColumnNames.DATE)
        )

        # Convert grouped signed totals into positive net-spend values
        daily_spending[ColumnNames.AMOUNT] = daily_spending[ColumnNames.AMOUNT].mul(-1).clip(lower=0)

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
    fig = create_line_chart(
        daily_spending,
        x=ColumnNames.DATE,
        y='cumulative_amount',
        x_title='Date',
        y_title="Cumulative Spending ($)",
    )
    fig.update_layout(margin={"l": 28, "r": 18, "t": 32, "b": 30})
    return fig


