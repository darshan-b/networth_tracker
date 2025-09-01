import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
from plotly.subplots import make_subplots
from plotly.graph_objs.treemap._marker import Marker
from pivot_table_view import show_pivot_table

# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(page_title="Net Worth Tracker", layout="wide")

# ----------------------------
# Load Data
# ----------------------------
data = pd.read_csv('Networth.csv')
data['Month'] = pd.to_datetime(data['Month'])
data['Amount'] = data['Amount'].round().astype(int)
# use this for visual purposes
data['Month_Str'] = data['Month'].dt.strftime('%b-%Y')
data = data.sort_values('Month')


# ----------------------------
# Shared Filters
st.header("Filters")

acct_types = sorted(data['Account Type'].unique())
selected_account_types = []
selected_account_types = st.segmented_control("Account Type", options=acct_types, selection_mode="multi", default=acct_types)

categories = data[data['Account Type'].isin(selected_account_types)]['Category'].unique() if selected_account_types else data['Category'].unique()
selected_categories = st.segmented_control("Category", options=categories, selection_mode="multi", default=categories)

accounts = data[
    data['Account Type'].isin(selected_account_types) & data['Category'].isin(selected_categories)
]['Account'].unique().tolist() if selected_account_types and selected_categories else data['Account'].unique()
selected_accounts = st.sidebar.multiselect("Account", options=accounts, default=accounts, key="acct_name")

# Apply filters
filtered_df = data[
    data['Account Type'].isin(selected_account_types) &
    data['Category'].isin(selected_categories) &
    data['Account'].isin(selected_accounts)
]

tab_1, tab_2, tab_3, tab_4 = st.tabs(["Detailed View", "Summarized Table", 'Line Chart', 'KPI'])


def round_to_k(amount):
    if amount >= 1000:
        return f"{amount/1000:.1f}k"  # Round to 1 decimal place and add 'k'
    else:
        return f"{amount:.0f}"
            

# -----------------------------------
# Detailed View of Networth Over Time
# -----------------------------------
with tab_1:
    st.header("Net Worth Over Time")

    # Aggregate for stacked bar
    agg_df = filtered_df.groupby(['Month', 'Month_Str', 'Category'], as_index=False)['Amount'].sum()
    totals_df = filtered_df.groupby(['Month', 'Month_Str'], as_index=False)['Amount'].sum()

    # Plotly stacked bar chart
    fig = px.bar(
        agg_df,
        x='Month',
        y='Amount',
        color='Category',
        text=None,
        barmode='stack',
        hover_data={'Month': False, 'Amount': True, 'Category': True},
        color_discrete_sequence=px.colors.qualitative.Light24
    )

    # Add total labels
    fig.add_trace(
        go.Scatter(
            x=totals_df['Month'],
            y=totals_df['Amount'],
            text=totals_df['Amount'].apply(lambda x: round_to_k(x)),
            textposition='top center',
            mode='text',
            showlegend=False,
            textfont=dict(size=14, color='black', family="Arial", weight='bold'),
            name='Total Amount'
        )
    )

    fig.update_layout(
        title="Net Worth Over Time",
        xaxis=dict(tickvals=totals_df['Month'], ticktext=totals_df['Month_Str'], title='Month', tickangle=90),
        yaxis=dict(title='Amount', tickprefix='$'),
        legend_title="Category",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Write to buffer
    buffer = io.StringIO()
    fig.write_html(buffer, full_html=False)
    buffer.seek(0)

    # Create a download button for the HTML file
    st.download_button(
        label="Download as HTML",
        data=buffer.getvalue(),
        file_name="net_worth_over_time.html",
        mime="application/vnd.ms-html"
    )


# ----------------------------
# Pivot Table View
# ----------------------------
with tab_2:
    show_pivot_table(filtered_df)


with tab_3:
    st.header("Month-over-Month Progress")

    grouped_df = filtered_df.groupby('Month')['Amount'].sum().reset_index()
    grouped_df['MoM_Pct_Change'] = grouped_df['Amount'].pct_change() * 100  # % change
    grouped_df['MoM_Pct_Change'] = grouped_df['MoM_Pct_Change'].round(2)
    grouped_df['Pct_Color'] = grouped_df['MoM_Pct_Change'].apply(lambda x: 'green' if x >=0 else 'red')
    # -----------------------------
    # Line Chart
    # -----------------------------
    x = grouped_df['Month']
    y = grouped_df['Amount']
    y_text = [f"{val/1000:.0f}k" for val in y]  # round to k
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode='lines+markers+text',
            text=y_text,
            textposition='top center',  # move text above markers
            textfont=dict(size=12, color='black', family='Arial, bold'),
            line=dict(color='blue', width=3),
            marker=dict(size=8),
            name='Total Amount'
        )
    )
    
    # Add MoM % change as secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=grouped_df['Month'],
            y=grouped_df['MoM_Pct_Change'],
            mode='lines+markers+text',
            text=grouped_df['MoM_Pct_Change'].apply(lambda x: f"{x:.2f}%"),
            textposition='bottom center',
            textfont=dict(color=grouped_df['Pct_Color'], size=12),
            line=dict(color='gray', dash='dot'),
            marker=dict(size=8, color=grouped_df['Pct_Color']),
            name='% Change',
            yaxis='y2'
        )
    )
    
    # -----------------------------
    # Update layout with secondary y-axis
    # -----------------------------
    fig.update_layout(
        xaxis_title="Month",
        yaxis=dict(title="Amount"),
        yaxis2=dict(
            title="% Change",
            overlaying='y',
            side='right',
            showgrid=False
        ),
        xaxis=dict(tickangle=-45),
        hovermode="x unified",
        template="plotly"
    )
    
    st.plotly_chart(fig, use_container_width=True)


with tab_4:
    st.header("Dashboard Overview")

    # -------------------------
    # Prepare the pivot table
    # -------------------------
    pivot = pd.pivot_table(
        filtered_df,
        values='Amount',
        index='Account Type',
        columns='Month_Str',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # Convert numeric columns to int
    numeric_cols = pivot.select_dtypes(include='number').columns
    pivot[numeric_cols] = pivot[numeric_cols].round(0).astype(int)

    # Prepare pivot table for go.Table
    pivot_text = pivot.astype(str)
    pivot_values = [pivot_text[col].tolist() for col in pivot_text.columns]

    # -------------------------
    # Prepare other charts
    # -------------------------
    # 1. Monthly total line chart
    monthly_total = filtered_df.groupby('Month_Str')['Amount'].sum().reset_index()

    # 2. Account Type distribution (bar)
    acct_total = filtered_df.groupby('Account Type')['Amount'].sum().reset_index()

    # -------------------------
    # Create subplot grid
    # -------------------------
    fig = make_subplots(
        rows=2, cols=1,
        specs=[[{"type": "treemap"}],
               [{"type": "pie"}]],
        subplot_titles=("Monthly Amounts", "Totals by Account", "Totals by Category (Treemap)", "Pivot Table Summary"),
        vertical_spacing=0.1,
        horizontal_spacing=0.08
    )

    # -------------------------
    # Add traces
    # -------------------------
    text_font = dict(size=12, color="black", family="Arial Black")

    latest_month = filtered_df['Month'].max()  # assuming 'Month' is datetime or sortable
    latest_df = filtered_df[filtered_df['Month'] == latest_month]
    
    treemap_df = latest_df.groupby(['Account Type', 'Category', 'Account'])['Amount'].sum().reset_index()
    treemap_df.loc[treemap_df['Account Type'] == 'Liability', 'Amount'] *= -1
    treemap_df['uuid'] = treemap_df['Account Type'] + treemap_df['Category'] + treemap_df['Account']

    # Original PX treemap
    px_fig = px.treemap(
        treemap_df, 
        path=[px.Constant("All"), 'Account Type', 'Category', 'Account'], 
        values='Amount',
        color='Amount',
        color_continuous_scale='viridis',  # keeps green/red gradient
        hover_data={'Amount': True}
    )
    
    # Add PX traces to subplot
    for trace in px_fig.data:
        trace.textinfo = 'label+value+percent parent'
        fig.add_trace((trace),row=1, col=1)
    
    fig.update_coloraxes(showscale=False)
    fig.update_traces(marker=dict(cornerradius=5))
    
    cat_total = latest_df.groupby('Category')['Amount'].sum().reset_index()
    # Pie chart
    fig.add_trace(
        go.Pie(
            labels=cat_total['Category'],
            values=cat_total['Amount'],
            name="Category Distribution",
            hole=0.4
        ),
        row=2, col=1
    )


    # -------------------------
    # Layout
    # -------------------------
    fig.update_layout(
        height=900,
        width=1200,
        showlegend=True,
        title_text="Dashboard Overview",
        title_x=0.5
    )

    st.plotly_chart(fig, use_container_width=True)