"""Expense tracker view with multiple sub-tabs.

Note: Transactions are stored with negative amounts for expenses and positive for income.
Income is identified by category == 'Income'.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import streamlit.components.v1 as components


from data.calculations import (
    calculate_expense_summary,
    calculate_category_spending,
    calculate_account_spending,
    calculate_budget_comparison,
    calculate_top_merchants,
    calculate_spending_by_dow,
    calculate_category_trends
)


def get_date_range_options():
    """Get standard date range options."""
    return [
        "Last 7 days",
        "Last 14 days", 
        "Last 30 days",
        "This month",
        "Last month",
        "This year",
        "Last year",
        "Custom range"
    ]


def apply_date_filter(df, date_option, key_prefix=""):
    """Apply date filter to dataframe based on selected option.
    
    Args:
        df: DataFrame to filter
        date_option: Selected date range option
        key_prefix: Prefix for streamlit widget keys
        
    Returns:
        Filtered DataFrame
    """
    if date_option == "Custom range":
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "Start date", 
                value=df['date'].min().date(), 
                key=f"{key_prefix}_start"
            )
        with col_end:
            end_date = st.date_input(
                "End date", 
                value=df['date'].max().date(), 
                key=f"{key_prefix}_end"
            )
        
        return df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]
    
    # Apply predefined date filters
    today = datetime.now()
    
    if date_option == "Last 7 days":
        return df[df['date'] >= (today - pd.Timedelta(days=7))]
    elif date_option == "Last 14 days":
        return df[df['date'] >= (today - pd.Timedelta(days=14))]
    elif date_option == "Last 30 days":
        return df[df['date'] >= (today - pd.Timedelta(days=30))]
    elif date_option == "This month":
        return df[(df['date'].dt.month == today.month) & (df['date'].dt.year == today.year)]
    elif date_option == "Last month":
        last_month = today.replace(day=1) - pd.Timedelta(days=1)
        return df[(df['date'].dt.month == last_month.month) & (df['date'].dt.year == last_month.year)]
    elif date_option == "This year":
        return df[df['date'].dt.year == today.year]
    elif date_option == "Last year":
        return df[df['date'].dt.year == (today.year - 1)]
    else:
        return df.copy()


def filter_expenses(df):
    """Filter dataframe for expenses only, excluding Income.
    
    Args:
        df: Transactions dataframe
        
    Returns:
        DataFrame with expenses only (category != 'Income')
    """
    return df[df['category'] != 'Income']



def render_expense_overview(df, budgets, num_months=1):
    """Render expense overview tab.
    
    Args:
        df: Transactions dataframe (already filtered by date and for expenses)
        budgets: Dictionary of monthly budgets by category
        num_months: Number of distinct months in the selected date range
    """
    st.subheader("📊 Expense Overview")
    
    # Get summary
    summary = calculate_expense_summary(df, budgets, num_months)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Spent", f"${summary['total_spent']:,.2f}")
    with col2:
        st.metric("Total Budget", f"${summary['total_budget']:,.2f}")
    with col3:
        remaining_pct = (summary['remaining'] / summary['total_budget'] * 100) if summary['total_budget'] > 0 else 0
        st.metric("Remaining", f"${summary['remaining']:,.2f}", delta=f"{remaining_pct:.1f}%")
    with col4:
        st.metric("Transactions", summary['num_transactions'])
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Spending by Category")
        category_spending = calculate_category_spending(df)
        
        if len(category_spending) > 0:
            fig = px.pie(
                category_spending, 
                values='amount', 
                names='category',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data for selected period")
    
    with col2:
        st.markdown("#### Spending Trend")
        
        # Filter controls
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            categories = ['All'] + sorted(df['category'].unique().tolist())
            selected_category = st.selectbox('Category', categories, key='trend_cat')
        
        with col_filter2:
            subcategories = ['All'] + sorted(df['subcategory'].unique().tolist())
            selected_subcategory = st.selectbox('Subcategory', subcategories, key='trend_subcat')
        
        with col_filter3:
            merchants = ['All'] + sorted(df['merchant'].unique().tolist())
            selected_merchant = st.selectbox('Merchant', merchants, key='trend_merch')
        
        # Apply filters
        filtered_df = df.copy()
        if selected_category != 'All':
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        if selected_subcategory != 'All':
            filtered_df = filtered_df[filtered_df['subcategory'] == selected_subcategory]
        if selected_merchant != 'All':
            filtered_df = filtered_df[filtered_df['merchant'] == selected_merchant]
        
        # Aggregate daily spending
        daily_spending = (
            filtered_df.groupby('date', as_index=False)['amount']
            .sum()
            .sort_values('date')
        )
        
        # Convert to positive values and calculate cumulative spending
        daily_spending['amount'] = daily_spending['amount'].abs()
        daily_spending['cumulative_amount'] = daily_spending['amount'].cumsum()
        
        # Create line chart
        fig = px.line(
            daily_spending, 
            x='date', 
            y='cumulative_amount',
            markers=True
        )
        
        # Customize appearance
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
        
        st.plotly_chart(fig, use_container_width=True)


def render_transactions(df):
    """Render transactions management tab.
    
    Args:
        df: Transactions dataframe (already filtered by date)
    """
    st.subheader("📝 Transactions")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        account_filter = st.multiselect(
            "Filter by Account", 
            options=sorted(df['account'].unique()),
            default=df['account'].unique()
        )
    
    with col2:
        category_filter = st.multiselect(
            "Filter by Category",
            options=sorted(df['category'].unique()),
            default=df['category'].unique()
        )
    
    with col3:
        search_merchant = st.text_input("Search Merchant", "")
    
    # Apply filters
    df_filtered = df[
        (df['account'].isin(account_filter)) &
        (df['category'].isin(category_filter))
    ]
    
    if search_merchant:
        df_filtered = df_filtered[
            df_filtered['merchant'].str.contains(search_merchant, case=False, na=False)
        ]
    
    # Display transactions
    df_display = df_filtered.sort_values('date', ascending=False).copy()
    
    # Create a display amount column (absolute value for expenses, positive for income)
    df_display['display_amount'] = df_display.apply(
        lambda row: abs(row['amount']) if row['category'] != 'Income' else row['amount'], 
        axis=1
    )
    
    st.dataframe(
        df_display[['date', 'merchant', 'category', 'account', 'display_amount']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "display_amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "date": st.column_config.DateColumn("Date"),
        }
    )
    
    # Summary metrics
    col1, col2 = st.columns(2)
    with col1:
        expenses_filtered = df_filtered[df_filtered['category'] != 'Income']
        expenses_total = abs(expenses_filtered['amount'].sum())
        st.metric("Total Expenses (Filtered)", f"${expenses_total:,.2f}")
    with col2:
        income_filtered = df_filtered[df_filtered['category'] == 'Income']
        income_total = income_filtered['amount'].sum()
        st.metric("Total Income (Filtered)", f"${income_total:,.2f}")


def render_budgets(df, budgets, num_months=1):
    """Render budget management tab.
    
    Args:
        df: Transactions dataframe (already filtered by date and for expenses)
        budgets: Dictionary of monthly budgets by category
        num_months: Number of distinct months in the selected date range
    """
    st.subheader("💵 Budget Management")
    
    # Show budget period info
    if num_months == 1:
        period_info = f"📅 Budget for 1 month"
    else:
        period_info = f"📅 Budget for {num_months} months"
    st.info(period_info)
    
    # Budget comparison
    budget_df = calculate_budget_comparison(df, budgets, num_months)
    
    st.markdown("#### Budget vs Actual (Selected Period)")
    
    if len(budget_df) > 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Budget', 
            x=budget_df['Category'], 
            y=budget_df['Budget'], 
            marker_color='lightblue'
        ))
        fig.add_trace(go.Bar(
            name='Spent', 
            x=budget_df['Category'], 
            y=budget_df['Spent'],
            marker_color='coral'
        ))
        
        fig.update_layout(barmode='group', xaxis_title="", yaxis_title="Amount ($)")
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Budget settings
    st.markdown("#### Monthly Budgets")
    
    col1, col2 = st.columns(2)
    
    for idx, (category, monthly_budget) in enumerate(budgets.items()):
        with col1 if idx % 2 == 0 else col2:
            row = budget_df[budget_df['Category'] == category].iloc[0] if category in budget_df['Category'].values else None
            spent = row['Spent'] if row is not None else 0
            scaled_budget = row['Budget'] if row is not None else monthly_budget
            percentage = row['Percentage'] if row is not None else 0
            
            st.write(f"**{category}**")
            
            # Display both monthly budget and scaled budget if different
            if num_months > 1:
                st.metric(
                    f"Budget ({num_months} months)", 
                    f"${scaled_budget:,.2f}",
                    delta=f"${spent:,.2f} spent"
                )
                st.caption(f"Monthly budget: ${monthly_budget:,.2f}")
            else:
                st.metric("Budget", f"${monthly_budget:,.2f}", delta=f"${spent:,.2f} spent")
            
            # Progress bar - clamp between 0 and 1
            progress_value = max(0.0, min(1.0, percentage / 100))
            st.progress(progress_value)
            
            # Color-coded caption
            if percentage > 100:
                st.error(f"⚠️ Over budget by ${spent - scaled_budget:,.2f} ({percentage:.1f}%)")
            elif percentage > 80:
                st.warning(f"${scaled_budget - spent:,.2f} remaining ({100 - percentage:.1f}%)")
            else:
                st.success(f"${scaled_budget - spent:,.2f} remaining ({100 - percentage:.1f}%)")
            
            st.divider()
    
    st.info("💡 **Read-only mode**: To modify budgets, edit your budgets.xlsx/csv file and reload the app.")


def render_insights(df):
    """Render insights tab.
    
    Args:
        df: Transactions dataframe (already filtered by date and for expenses)
    """
    st.subheader("📈 Financial Insights")
    
    # Top merchants
    st.markdown("#### Top Merchants")
    top_merchants = calculate_top_merchants(df, 10)
    
    if len(top_merchants) > 0:
        fig = px.bar(
            top_merchants, 
            x='amount', 
            y='merchant', 
            orientation='h',
            color='amount',
            color_continuous_scale='Reds'
        )
        fig.update_layout(showlegend=False, xaxis_title="Amount ($)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Spending patterns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Spending by Day of Week")
        dow_spending = calculate_spending_by_dow(df)
        
        fig = px.bar(
            dow_spending, 
            x='day_of_week', 
            y='amount',
            color='amount',
            color_continuous_scale='Greens'
        )
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Amount ($)")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Average Transaction by Category")
        avg_by_category = df.groupby('category')['amount'].apply(
            lambda x: abs(x.mean())
        ).sort_values(ascending=False).reset_index()
        
        fig = px.bar(
            avg_by_category, 
            x='category', 
            y='amount',
            color='amount',
            color_continuous_scale='Purples'
        )
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Average ($)")
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Transactions", len(df))
        avg_amount = abs(df['amount'].mean())
        st.metric("Average Transaction", f"${avg_amount:.2f}")
    
    with col2:
        largest_amount = abs(df['amount'].min())  # Most negative = largest expense
        st.metric("Largest Transaction", f"${largest_amount:.2f}")
        if len(df) > 0:
            largest = df.loc[df['amount'].idxmin()]
            st.caption(f"{largest['merchant']} - {largest['category']}")
    
    with col3:
        if len(df) > 0:
            st.metric("Most Frequent Merchant", df['merchant'].mode()[0])
            st.metric("Most Frequent Category", df['category'].mode()[0])
    
    st.divider()
    
    # Category breakdown over time
    st.markdown("#### Category Spending Over Time")
    category_monthly = calculate_category_trends(df)
    
    if len(category_monthly) > 0:
        fig = px.line(
            category_monthly, 
            x='month', 
            y='amount', 
            color='category',
            markers=True
        )
        fig.update_layout(
            xaxis_title="Month", 
            yaxis_title="Amount ($)",
            xaxis=dict(tickformat="%b %Y")  # Format as "Jan 2024"
        )
        st.plotly_chart(fig, use_container_width=True)


def render_cashflow_sankey(df):
    """Render Sankey diagram for cash flow visualization using D3.js.
    
    Args:
        df: DataFrame (already filtered by date and for expenses)
    """
    st.subheader("💰 Cash Flow")
    
    # Calculate total (use absolute value)
    total_expenses = abs(df['amount'].sum())
    
    # Prepare data for D3
    nodes = []
    links = []
    node_map = {}
    
    # Color scheme
    color_map = {
        'Total': '#3b82f6',
        'Housing': '#ef4444',
        'Utilities': '#f59e0b',
        'Food & Dining': '#10b981',
        'Entertainment': '#8b5cf6',
        'Transportation': '#ec4899',
        'Miscellaneous': '#6b7280',
    }
    
    # Add total node
    nodes.append({
        "name": "Total Expenses",
        "displayName": f"Total Expenses<br/>${total_expenses:,.2f}",
        "color": color_map['Total']
    })
    node_map['Total'] = 0
    node_idx = 1
    
    # Group by category (use absolute values)
    category_totals = df.groupby('category')['amount'].apply(
        lambda x: abs(x.sum())
    ).sort_values(ascending=False)
    
    # Add category nodes and links
    for category, amount in category_totals.items():
        pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
        nodes.append({
            "name": category,
            "displayName": f"{category}<br/>${amount:,.2f} ({pct:.1f}%)",
            "color": color_map.get(category, '#94a3b8')
        })
        node_map[category] = node_idx
        links.append({
            "source": 0,
            "target": node_idx,
            "value": float(amount)
        })
        node_idx += 1
    
    # Add subcategory nodes
    for category in category_totals.index:
        category_df = df[df['category'] == category]
        subcategory_df = category_df[
            category_df['subcategory'].notna() & 
            (category_df['subcategory'] != '')
        ]
        
        if len(subcategory_df) > 0:
            subcategory_totals = subcategory_df.groupby('subcategory')['amount'].apply(
                lambda x: abs(x.sum())
            ).sort_values(ascending=False)
            
            for subcategory, amount in subcategory_totals.items():
                category_total = category_totals[category]
                pct = (amount / category_total * 100) if category_total > 0 else 0
                nodes.append({
                    "name": subcategory,
                    "displayName": f"{subcategory}<br/>${amount:,.2f} ({pct:.1f}%)",
                    "color": color_map.get(category, '#94a3b8')
                })
                links.append({
                    "source": node_map[category],
                    "target": node_idx,
                    "value": float(amount)
                })
                node_idx += 1
    
    data = {"nodes": nodes, "links": links}
    
    # D3.js HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <script src="https://unpkg.com/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: white;
            }}
            #chart {{ background: white; }}
            .node rect {{
                stroke: #fff;
                stroke-width: 2px;
                cursor: pointer;
            }}
            .node rect:hover {{ opacity: 0.8; }}
            .link {{
                fill: none;
                stroke-opacity: 0.4;
            }}
            .link:hover {{ stroke-opacity: 0.7; }}
            .node-label {{
                font-size: 14px;
                font-weight: 500;
                pointer-events: none;
            }}
            .title {{
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="title">Cash Flow Visualization</div>
        <svg id="chart"></svg>
        <script>
            const data = {json.dumps(data)};
            
            const width = 1400;
            const height = 800;
            
            const svg = d3.select("#chart")
                .attr("width", width)
                .attr("height", height)
                .attr("viewBox", [0, 0, width, height]);
            
            const sankey = d3.sankey()
                .nodeId(d => d.index)
                .nodeWidth(35)
                .nodePadding(25)
                .extent([[1, 1], [width - 1, height - 6]]);
            
            data.nodes.forEach((node, i) => node.index = i);
            
            const graph = sankey(data);
            
            // Add links
            const link = svg.append("g")
                .attr("class", "links")
                .selectAll("path")
                .data(graph.links)
                .join("path")
                .attr("class", "link")
                .attr("d", d3.sankeyLinkHorizontal())
                .attr("stroke", d => d.source.color)
                .attr("stroke-width", d => Math.max(1, d.width))
                .style("stroke-opacity", 0.4);
            
            link.append("title")
                .text(d => d.source.name + ' → ' + d.target.name + '\\n$' + 
                      d.value.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}));
            
            // Add nodes
            const node = svg.append("g")
                .attr("class", "nodes")
                .selectAll("g")
                .data(graph.nodes)
                .join("g");
            
            node.append("rect")
                .attr("x", d => d.x0)
                .attr("y", d => d.y0)
                .attr("height", d => d.y1 - d.y0)
                .attr("width", d => d.x1 - d.x0)
                .attr("fill", d => d.color);
            
            node.append("title")
                .text(d => d.displayName.replace(/<br\\/>/g, '\\n'));
            
            // Add labels
            node.append("foreignObject")
                .attr("x", d => d.x0 < width / 2 ? d.x1 + 8 : d.x0 - 8)
                .attr("y", d => (d.y1 + d.y0) / 2 - 30)
                .attr("width", 200)
                .attr("height", 60)
                .attr("text-anchor", d => d.x0 < width / 2 ? "start" : "end")
                .append("xhtml:div")
                .attr("class", "node-label")
                .style("text-align", d => d.x0 < width / 2 ? "left" : "right")
                .html(d => d.displayName);
        </script>
    </body>
    </html>
    """
    
    components.html(html_content, height=900, scrolling=False)
    
    # Summary metrics
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Expenses", f"${total_expenses:,.2f}")
    
    with col2:
        num_categories = len(category_totals)
        st.metric("Categories", num_categories)
    
    with col3:
        if len(category_totals) > 0:
            largest_category = category_totals.index[0]
            largest_amount = category_totals.iloc[0]
            st.metric("Largest Category", largest_category)
            st.caption(f"${largest_amount:,.2f}")
    
    with col4:
        avg_transaction = abs(df['amount'].mean())
        st.metric("Avg Transaction", f"${avg_transaction:,.2f}")


def show_expense_tracker(df_filtered, budgets, num_months=1):
    """Main expense tracker view with sub-tabs."""
    # Load data

    

    
    st.divider()
    
    # Create sub-tabs
    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs([
        "Overview", 
        "Transactions", 
        "Budgets", 
        "Insights",
        "Sankey Chart"
    ])
    
    # Filter for expenses for tabs that need it
    df_expenses = filter_expenses(df_filtered)
    
    with sub_tab1:
        render_expense_overview(df_expenses, budgets, num_months)
    
    with sub_tab2:
        render_transactions(df_filtered)  # Show all transactions
    
    with sub_tab3:
        render_budgets(df_expenses, budgets, num_months)
    
    with sub_tab4:
        render_insights(df_expenses)
    
    with sub_tab5:
        render_cashflow_sankey(df_expenses)