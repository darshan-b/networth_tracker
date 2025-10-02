import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
from plotly.subplots import make_subplots
from plotly.graph_objs.treemap._marker import Marker
from pivot_table_view import show_pivot_table
from detailed_view import show_detailed_view
import os

# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(page_title="Net Worth Tracker", layout="wide")

# ----------------------------
# Load Data
# ----------------------------
# Get the directory of the currently running script (networth.py)
base_path = os.path.dirname(os.path.abspath(__file__))

# Build full path to CSV
csv_path = os.path.join(base_path, "Networth.csv")

data = pd.read_csv(csv_path)
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

# ----------------------------
# Account Filter in Sidebar
# ----------------------------
st.sidebar.markdown("### 🏦 Account Filter")

# Initialize session state for selected accounts
if 'selected_accounts' not in st.session_state:
    st.session_state.selected_accounts = accounts.copy()

# Initialize session state for expander states
if 'expander_states' not in st.session_state:
    st.session_state.expander_states = {}

# Get latest month data for account values
latest_month = data['Month'].max()

# Create account info dict with current values and trends
account_info = {}
for account in accounts:
    acct_data = data[data['Account'] == account].sort_values('Month')
    if len(acct_data) >= 2:
        current_val = acct_data.iloc[-1]['Amount']
        prev_val = acct_data.iloc[-2]['Amount']
        change = current_val - prev_val
        trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
    elif len(acct_data) == 1:
        current_val = acct_data.iloc[-1]['Amount']
        change = 0
        trend = "➡️"
    else:
        continue
    
    account_info[account] = {
        'value': current_val,
        'change': change,
        'trend': trend,
        'type': acct_data.iloc[-1]['Account Type']
    }

# Search box
search = st.sidebar.text_input("🔍 Search accounts", "", placeholder="Type to filter...")

# Filter accounts based on search
filtered_accounts = [a for a in accounts if search.lower() in a.lower()] if search else accounts

# Group accounts by type first (needed for expand/collapse)
grouped_accounts = {}
for acc in filtered_accounts:
    acct_type = account_info.get(acc, {}).get('type', 'Unknown')
    if acct_type not in grouped_accounts:
        grouped_accounts[acct_type] = []
    grouped_accounts[acct_type].append(acc)

# Initialize expander states for any new account types
for acct_type in grouped_accounts.keys():
    if acct_type not in st.session_state.expander_states:
        st.session_state.expander_states[acct_type] = True  # Default to expanded

# Check if most expanders are currently expanded
expanded_count = sum(1 for state in st.session_state.expander_states.values() if state)
total_count = len(st.session_state.expander_states)
mostly_expanded = expanded_count > total_count / 2 if total_count > 0 else True

# Quick actions - 3 columns now
col1, col2, col3 = st.sidebar.columns(3)
with col1:
    if st.button("✅", use_container_width=True, help="Select all accounts"):
        st.session_state.selected_accounts = accounts.copy()
with col2:
    if st.button("❌", use_container_width=True, help="Clear all accounts"):
        st.session_state.selected_accounts = []
with col3:
    # Toggle button - shows opposite of current state
    toggle_icon = "➖" if mostly_expanded else "➕"
    toggle_help = "Collapse all groups" if mostly_expanded else "Expand all groups"
    if st.button(toggle_icon, use_container_width=True, help=toggle_help):
        new_state = not mostly_expanded
        for acct_type in grouped_accounts.keys():
            st.session_state.expander_states[acct_type] = new_state

# Grouped display
for acct_type in sorted(grouped_accounts.keys()):
    accts = grouped_accounts[acct_type]
    is_expanded = st.session_state.expander_states.get(acct_type, True)
    
    with st.sidebar.expander(f"📁 {acct_type} ({len(accts)})", expanded=is_expanded):
        # Group controls - also compact
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅", use_container_width=True, key=f"all_{acct_type}", help=f"Select all {acct_type}"):
                # Add all accounts from this group
                current = set(st.session_state.selected_accounts)
                current.update(accts)
                st.session_state.selected_accounts = list(current)
        with col2:
            if st.button("❌", use_container_width=True, key=f"none_{acct_type}", help=f"Clear all {acct_type}"):
                # Remove all accounts from this group
                st.session_state.selected_accounts = [a for a in st.session_state.selected_accounts if a not in accts]
        
        # Individual checkboxes
        for acc in accts:
            info = account_info.get(acc, {})
            label = f"{acc} ({info.get('trend', '➡️')} ${info.get('value', 0):,.0f})" if info else acc
            is_selected = acc in st.session_state.selected_accounts
            
            if st.checkbox(label, value=is_selected, key=f"check_{acc}"):
                if acc not in st.session_state.selected_accounts:
                    st.session_state.selected_accounts.append(acc)
            else:
                if acc in st.session_state.selected_accounts:
                    st.session_state.selected_accounts.remove(acc)

selected_accounts = st.session_state.selected_accounts

# Summary statistics
st.sidebar.divider()
count = len(selected_accounts)
total = len(accounts)

if count > 0:
    selected_value = sum(account_info.get(a, {}).get('value', 0) for a in selected_accounts)
    total_value = sum(account_info.get(a, {}).get('value', 0) for a in accounts)
    
    if count == total:
        st.sidebar.success(f"✓ {count} of {total} selected")
    else:
        st.sidebar.info(f"✓ {count} of {total} selected")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Selected", f"${selected_value:,.0f}")
    with col2:
        pct = (selected_value / total_value * 100) if total_value != 0 else 0
        st.metric("% of Total", f"{pct:.1f}%")
else:
    st.sidebar.error("⚠️ No accounts selected")

if search:
    st.sidebar.caption(f"🔍 {len(filtered_accounts)} matches")

# ----------------------------
# Apply filters
# ----------------------------
filtered_df = data[
    data['Account Type'].isin(selected_account_types) &
    data['Category'].isin(selected_categories) &
    data['Account'].isin(selected_accounts)
]

tab_1, tab_2, tab_3, tab_4 = st.tabs(["Detailed View", "Summarized Table", 'Line Chart', 'KPI'])

            
# -----------------------------------
# Detailed View of Networth Over Time
# -----------------------------------
with tab_1:
    show_detailed_view(filtered_df)


# ----------------------------
# Pivot Table View
# ----------------------------
with tab_2:
    show_pivot_table(filtered_df)


with tab_3:
    st.header("Month-over-Month Progress")

    # -----------------------------
    # Prepare data for Assets & Liabilities
    # -----------------------------
    assets_df = filtered_df[filtered_df['Account Type'] != 'Liability'].groupby('Month')['Amount'].sum().reset_index()
    liabilities_df = filtered_df[filtered_df['Account Type'] == 'Liability'].groupby('Month')['Amount'].sum().reset_index()

    grouped_df = assets_df.merge(liabilities_df, on='Month', how='outer', suffixes=('_Assets', '_Liabilities')).fillna(0)
    grouped_df['Total'] = grouped_df['Amount_Assets'] - grouped_df['Amount_Liabilities']  # Net Worth

    # Calculate MoM % Change based on Net Worth or Total Amount
    grouped_df['MoM_Pct_Change'] = grouped_df['Total'].pct_change() * 100
    grouped_df['MoM_Pct_Change'] = grouped_df['MoM_Pct_Change'].round(2)
    grouped_df['Pct_Color'] = grouped_df['MoM_Pct_Change'].apply(lambda x: 'green' if x >= 0 else 'red')

    # -----------------------------
    # Create figure
    # -----------------------------
    fig = go.Figure()

    # Assets Area
    fig.add_trace(go.Scatter(
        x=grouped_df['Month'],
        y=grouped_df['Amount_Assets'],
        mode='lines',
        name='Assets',
        line=dict(color='green'),
        fill='tozeroy',
        opacity=0.6
    ))

    # Liabilities Area
    fig.add_trace(go.Scatter(
        x=grouped_df['Month'],
        y=grouped_df['Amount_Liabilities'],
        mode='lines',
        name='Liabilities',
        line=dict(color='red'),
        fill='tozeroy',
        opacity=0.6
    ))

    # MoM % change line on secondary axis
    fig.add_trace(go.Scatter(
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
    ))

    # -----------------------------
    # Layout
    # -----------------------------
    fig.update_layout(
        title="Assets vs Liabilities with MoM Change",
        xaxis_title="Month",
        yaxis=dict(title="Amount"),
        yaxis2=dict(
            title="% Change",
            overlaying='y',
            side='right',
            showgrid=False
        ),
        xaxis=dict(tickangle=-90),
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