"""Insights tab for expense tracker.

Provides analytical insights including top merchants, spending patterns, and trends.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import ChartConfig
from ui.charts import create_bar_chart, create_line_chart
from data.calculations import (
    calculate_category_spending,
    calculate_expense_summary,
    calculate_net_outflow,
    calculate_monthly_cash_flow,
    calculate_subcategory_spending,
    calculate_top_merchants,
    calculate_spending_by_dow,
    calculate_category_trends,
    is_income_transaction,
    is_expense_transaction,
)
from data.expense_intelligence import (
    get_month_over_month_change,
    get_spend_anomaly,
    get_spend_recommendations,
    get_top_change_driver,
)
from app_constants import ColumnNames
from ui.components.surfaces import (
    inject_surface_styles,
    render_accent_pills,
    render_metric_card,
    render_page_hero,
    render_section_intro,
)
import plotly.io as pio
pio.templates.default = ChartConfig.TEMPLATE



def render_insights_tab(df):
    """
    Render the financial insights tab with various analytical visualizations.
    
    Args:
        df (pd.DataFrame): Transactions dataframe filtered for expenses only
        
    Returns:
        None
    """
    inject_surface_styles()
    render_page_hero(
        "Expenses",
        "Insights",
        "Look for concentration, timing, and category patterns in spending behavior.",
        "Use this tab for patterns and breakdowns rather than raw transactions.",
    )
    
    if df.empty:
        st.info("No expense data available for the selected period.")
        return
    
    df = df[df[ColumnNames.SUBCATEGORY]!='Transfer']
    
    render_section_intro("Cash Flow", "Review the monthly relationship between income, expenses, and savings.")
    _render_cash_flow(df)
    _render_change_story(df)
    _render_recommendations(df)
    
    render_section_intro("Snapshot", "Review the biggest spending patterns before drilling into category breakdowns.")
    _render_summary_statistics(df)

    render_section_intro("Breakdown", "See where spending is concentrated across merchants, categories, and subcategories.")
    col1, col2 = st.columns([0.62, 0.38])
    with col1:
        _render_top_merchants(df)

    with col2:
        _render_dow_spending(df)
    
    st.divider()
    render_section_intro(
        "Trends",
        "Track how category spending shifts over time.",
    )
    _render_category_trends(df)


def _render_top_merchants(df):
    """
    Render horizontal bar chart of top merchants by spending.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    st.markdown("#### Spending Breakdown")
    
    try:
        expense_df = df[is_expense_transaction(df)].copy()
        if expense_df.empty:
            st.info("No expense rows available for breakdown analysis.")
            return

        top_merchants = calculate_top_merchants(df, limit=10)
        category_spending = calculate_category_spending(df)
        top_categories = category_spending.head(10).reset_index()
        top_subcategories = calculate_subcategory_spending(df).head(10).reset_index()
        total_spend = float(category_spending.sum())
        top_category = top_categories.iloc[0] if not top_categories.empty else None
        render_accent_pills(
            [
                ("Spend Rows", f"{len(expense_df):,}"),
                ("Merchants", str(expense_df[ColumnNames.MERCHANT].nunique())),
                ("Largest Category", f"{top_category[ColumnNames.CATEGORY] if top_category is not None else 'N/A'}"),
                ("Largest Share", f"{(top_category[ColumnNames.AMOUNT] / total_spend * 100):.1f}%" if top_category is not None and total_spend else "0%"),
            ]
        )

        selected = st.segmented_control(
            "View",
            ["By Merchant", "By Category", "By Subcategory"],
            default="By Merchant",
            label_visibility="collapsed",
            width="stretch",
        )

        if selected == "By Merchant":
            fig = create_bar_chart(
                pd.Series(top_merchants[ColumnNames.AMOUNT].values, index=top_merchants[ColumnNames.MERCHANT].values),
                orientation='h',
                color_scheme='networth',
            )
        elif selected == "By Category":
            fig = create_bar_chart(
                pd.Series(top_categories[ColumnNames.AMOUNT].values, index=top_categories[ColumnNames.CATEGORY].values),
                orientation='h',
                color_scheme='networth',
            )
        else:
            fig = create_bar_chart(
                pd.Series(top_subcategories[ColumnNames.AMOUNT].values, index=top_subcategories[ColumnNames.SUBCATEGORY].values),
                orientation='h',
                color_scheme='networth',
            )

        fig.update_yaxes(categoryorder='total ascending')
        st.plotly_chart(fig, config={"responsive": True})
        
    except Exception as e:
        st.error(f"Error rendering top merchants: {str(e)}")


def _render_change_story(df: pd.DataFrame) -> None:
    """Summarize what changed recently and what drove it."""
    change = get_month_over_month_change(df)
    if not change:
        return

    render_section_intro(
        "What Changed",
        "Start with the biggest movement from the previous month and the likely driver behind it.",
    )

    driver = get_top_change_driver(df, change["current_month"], change["previous_month"])
    anomaly = get_spend_anomaly(df)

    render_accent_pills(
        [
            ("Spend", _format_change_pill(change["spending_delta"], change["spending_pct"])),
            ("Income", _format_change_pill(change["income_delta"], change["income_pct"])),
            ("Savings", _format_change_pill(change["savings_delta"], change["savings_pct"])),
            *([("Top Driver", f"{driver['category']} ${abs(driver['delta']):,.0f}")] if driver else []),
            *([("Anomaly", f"{anomaly['date']}: {anomaly['multiple']:.1f}x typical")] if anomaly else []),
        ]
    )


def _format_change_pill(delta: float, pct: float) -> str:
    """Format a compact month-over-month delta label."""
    return f"{delta:+,.0f} ({pct:+.1f}%)"


def _render_recommendations(df: pd.DataFrame) -> None:
    """Show a concise set of actions from the current insight signals."""
    recommendations = get_spend_recommendations(df)
    if not recommendations:
        return

    render_section_intro(
        "Recommended Actions",
        "Use these signals to decide where to investigate before drilling into raw rows.",
    )
    render_accent_pills([(f"Action {idx}", text) for idx, text in enumerate(recommendations, start=1)])


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
        
        fig = create_bar_chart(
            pd.Series(dow_spending[ColumnNames.AMOUNT].values, index=dow_spending['day_of_week'].values),
            orientation='v',
            color_scheme='networth',
            show_values=False,
            y_label='Amount ($)',
        )
        st.plotly_chart(fig, config={"responsive": True})
        
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
        expense_df = df[is_expense_transaction(df)].copy()
        avg_by_category = (
            expense_df.groupby(ColumnNames.CATEGORY)[ColumnNames.AMOUNT]
            .apply(lambda x: abs(x.mean()))
            .sort_values(ascending=False)
            .reset_index()
        )
        
        if avg_by_category.empty:
            st.info("No category data available.")
            return
        
        fig = px.bar(
            avg_by_category, 
            x=ColumnNames.CATEGORY, 
            y=ColumnNames.AMOUNT,
            color=ColumnNames.AMOUNT,
            color_continuous_scale='Purples'
        )
        fig.update_layout(
            showlegend=False, 
            xaxis_title="", 
            yaxis_title="Average ($)"
        )
        st.plotly_chart(fig, config={"responsive": True})
        
    except Exception as e:
        st.error(f"Error rendering average transactions: {str(e)}")


def _render_summary_statistics(df):
    """
    Display summary statistics in a three-column layout.
    
    Args:
        df (pd.DataFrame): Transactions dataframe
    """
    # Calculate some reusable values
    expense_df = df[is_expense_transaction(df)].copy()
    if expense_df.empty:
        st.info("No expense rows available for summary analysis.")
        return
    summary = calculate_expense_summary(df, budgets={}, num_months=1)
    total_amount = summary["total_spent"]
    category_spending = calculate_category_spending(df)
    monthly_net_spend = calculate_monthly_cash_flow(df)
    non_income_df = df[~is_income_transaction(df)].copy()

    # Row 1: Core spending metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric_card("Total Spend", f"${total_amount:,.0f}", "Selected period", "Net spend after refunds and credits.", "negative")

    with col2:
        avg_amount = abs(expense_df[ColumnNames.AMOUNT].mean()) if not expense_df.empty else 0
        render_metric_card("Average Transaction", f"${avg_amount:,.0f}", "Per transaction", "Average amount per expense transaction.", "neutral")

    with col3:
        median_amount = abs(expense_df[ColumnNames.AMOUNT].median()) if not expense_df.empty else 0
        render_metric_card("Median Transaction", f"${median_amount:,.0f}", "Typical size", "Median amount per expense transaction.", "neutral")

    # Row 2: Transaction counts and daily average
    col4, col5 = st.columns(2)
    with col4:
        largest_amount = abs(expense_df[ColumnNames.AMOUNT].min()) if not expense_df.empty else 0
        largest_caption = "Largest single expense in view."
        if not expense_df.empty:
            try:
                largest = expense_df.loc[expense_df[ColumnNames.AMOUNT].idxmin()]
                largest_caption = f"{largest[ColumnNames.MERCHANT]} - {largest[ColumnNames.CATEGORY]}"
            except Exception:
                pass
        render_metric_card("Largest Transaction", f"${largest_amount:,.0f}", "High watermark", largest_caption, "negative")

    with col5:
        daily_totals = (
            non_income_df.groupby(non_income_df[ColumnNames.DATE].dt.date)[ColumnNames.AMOUNT]
            .sum()
            .pipe(calculate_net_outflow)
            if not non_income_df.empty else pd.Series(dtype=float)
        )
        if daily_totals.empty:
            render_metric_card("Most Expensive Day", "N/A", "$0", "No daily spend totals available.", "neutral")
        else:
            most_expensive_day = daily_totals.idxmax()
            most_expensive_amount = daily_totals.max()
            render_metric_card("Most Expensive Day", most_expensive_day.strftime("%b %d, %Y"), f"${most_expensive_amount:,.0f}", "Highest daily spend total in the period.", "neutral")

    # Row 4: Category insights
    col6, col7 = st.columns(2)
    with col6:
        if not expense_df.empty:
            try:
                most_frequent_merchant = expense_df[ColumnNames.MERCHANT].mode()[0]
                render_metric_card("Most Frequent Merchant", most_frequent_merchant, "Repeated most often", "Merchant with the highest transaction frequency.", "neutral")
            except Exception:
                st.info("Insufficient data")

    with col7:
        if not expense_df.empty:
            try:
                most_frequent_category = expense_df[ColumnNames.CATEGORY].mode()[0]
                render_metric_card("Most Frequent Category", most_frequent_category, "Repeated most often", "Category with the highest transaction frequency.", "neutral")
            except Exception:
                st.info("Insufficient data")

    col8, col9 = st.columns(2)
    with col8:
        # Row 8: Month-over-month change (if applicable)
        if len(monthly_net_spend) > 1:
            current_row = monthly_net_spend.iloc[-1]
            prev_row = monthly_net_spend.iloc[-2]
            current_total = current_row["expenses"]
            prev_total = prev_row["expenses"]
            if prev_total > 0 or current_total > 0:
                change_pct = ((current_total - prev_total) / prev_total * 100) if prev_total > 0 else 0

                render_metric_card(
                    "Current Month Spending",
                    f"${current_total:,.0f}",
                    f"{change_pct:+.1f}% vs previous month",
                    "Latest month compared with the prior month.",
                    "negative" if change_pct > 0 else "positive" if change_pct < 0 else "neutral",
                )

    with col9:
        if category_spending.empty:
            render_metric_card("Top Spending Category", "N/A", "0.0% of total", "$0 of total spend.", "neutral")
        else:
            top_category = category_spending.idxmax()
            top_category_amount = category_spending.max()
            percentage = (top_category_amount / total_amount) * 100 if total_amount else 0
            render_metric_card("Top Spending Category", top_category, f"{percentage:.1f}% of total", f"${top_category_amount:,.0f} of total spend.", "neutral")


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
        
        fig = create_line_chart(
            category_monthly,
            x=ColumnNames.MONTH,
            y=ColumnNames.AMOUNT,
            color=ColumnNames.CATEGORY,
            x_title="Month",
            y_title="Amount ($)",
        )
        fig.update_xaxes(tickformat="%b %Y")
        st.plotly_chart(fig, config={"responsive": True})
        
    except Exception as e:
        st.error(f"Error rendering category trends: {str(e)}")


def _render_cash_flow(df):
    st.markdown("#### Monthly Cash Flow")

    # Create figure
    fig = go.Figure()

    cash_flow = calculate_monthly_cash_flow(df)
    if cash_flow.empty:
        st.info("No monthly cash-flow data available.")
        return

    month_labels = cash_flow[ColumnNames.MONTH].dt.strftime("%b %Y")

    # Add positive bars (green)
    fig.add_trace(go.Bar(
        x=month_labels,
        y=cash_flow["income"],
        marker_color='rgba(144, 238, 144, 0.9)',
        hovertemplate='Income: %{y:$,.0f}<extra></extra>',
        name='Income',
        textposition='inside',
        text = cash_flow["income"],
        texttemplate='$%{text:,.0f}',
        insidetextanchor='start' 
    ))

    # Add negative bars (red/pink)
    fig.add_trace(go.Bar(
        x=month_labels,
        y=-cash_flow["expenses"],
        marker_color='rgba(255, 182, 193, 0.9)',
        hovertemplate='Expenses: %{y:$,.0f}<extra></extra>',
        name='Expenses',
        textposition='inside',
        text = cash_flow["expenses"],
        texttemplate='$%{text:,.0f}',
        insidetextanchor='start' 
    ))

    # Add solid line for savings
    fig.add_trace(go.Scatter(
        x=month_labels, 
        y=cash_flow["savings"],
        mode='lines+markers',
        name='Savings',
        line=dict(color='blue', width=2, dash='dash'),
        hovertemplate='Savings: %{y:$,.0f}<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        barmode='relative',  # Stack bars
        height=400,
        margin=dict(l=36, r=24, t=56, b=42),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(248,250,252,0.55)",
        xaxis=dict(
            showgrid=False,
            showline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(148, 163, 184, 0.14)',
            showline=False,
            tickformat='$,.0f',
            tickprefix='',
            zeroline=False,
            nticks=5,
        ),
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        template=ChartConfig.TEMPLATE,
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.96)",
            bordercolor="rgba(15, 23, 42, 0.10)",
            font=dict(
                family=ChartConfig.FONT["family"],
                size=13,
                color="#0f172a",
            ),
        ),
        font=ChartConfig.FONT,
    )
    fig.update_traces(
        selector=dict(type="bar"),
        marker_line_width=0,
        marker_line_color="rgba(0,0,0,0)",
        marker=dict(cornerradius=10),
    )
    st.plotly_chart(fig, config={"responsive": True})
