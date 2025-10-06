"""Detailed view for Net Worth Tracker - Shows trends over time."""

import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from constants import ColumnNames


def round_to_k(amount):
    """Round large amounts to 'k' notation."""
    if amount >= 1000:
        return f"{amount/1000:.1f}k"
    else:
        return f"{amount:.0f}"


def show_growth_over_time(filtered_df):
    """
    Main function to display the detailed view tab.
    
    Args:
        filtered_df: Filtered dataset based on user selections
    """
    st.header("Net Worth Over Time")
    
    # Validate data
    if filtered_df.empty:
        st.warning("No data available. Please adjust your filters.")
        return
    
    # -------------------------
    # Summary Statistics
    # -------------------------
    st.subheader("Quick Stats")
    
    totals_df = filtered_df.groupby([ColumnNames.MONTH, 'month_Str'], as_index=False)[ColumnNames.AMOUNT].sum()
    
    if len(totals_df) >= 2:
        current_nw = totals_df.iloc[-1][ColumnNames.AMOUNT]
        previous_nw = totals_df.iloc[-2][ColumnNames.AMOUNT]
        first_nw = totals_df.iloc[0][ColumnNames.AMOUNT]
        
        mom_change = current_nw - previous_nw
        mom_pct = (mom_change / abs(previous_nw)) * 100 if previous_nw != 0 else 0
        
        total_change = current_nw - first_nw
        total_pct = (total_change / abs(first_nw)) * 100 if first_nw != 0 else 0
        
        # Calculate average monthly growth
        avg_monthly_growth = total_change / len(totals_df) if len(totals_df) > 0 else 0
        
        # Calculate growth velocity
        if len(totals_df) >= 3:
            prev_period_change = totals_df.iloc[-2][ColumnNames.AMOUNT] - totals_df.iloc[-3][ColumnNames.AMOUNT]
            velocity = mom_change - prev_period_change
            if velocity > 0:
                velocity_text = "Accelerating"
            elif velocity < 0:
                velocity_text = "Decelerating"
            else:
                velocity_text = "Steady"
        else:
            velocity_text = "N/A"
        
        # Find best and worst months
        best_idx = totals_df[ColumnNames.AMOUNT].idxmax()
        worst_idx = totals_df[ColumnNames.AMOUNT].idxmin()
        best_month = totals_df.loc[best_idx, 'month_Str']
        worst_month = totals_df.loc[worst_idx, 'month_Str']
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Current Net Worth", f"${current_nw:,.0f}", 
                     f"{mom_change:,.0f} ({mom_pct:+.2f}%)")
        with col2:
            st.metric("Total Growth", f"${total_change:,.0f}", f"{total_pct:+.2f}%")
        with col3:
            st.metric("months Tracked", len(totals_df))
        with col4:
            st.metric("Growth Momentum", velocity_text)
        with col5:
            st.metric("Avg monthly Growth", f"${avg_monthly_growth:,.0f}")
    else:
        st.warning("Need at least 2 months of data for analysis.")
        return
    
    st.divider()
    
    # -------------------------
    # Controls
    # -------------------------
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        breakdown_by = st.selectbox("Breakdown By:", [ColumnNames.CATEGORY, ColumnNames.ACCOUNT_TYPE, "Both"], key="breakdown")
    
    with col2:
        view_preset = st.selectbox(
            "Chart View:", 
            ["Standard", "With Trend Line", "With 3-month Average"],
            index=1,
            help="Standard: Basic stacked bars | Trend Line: Adds net worth trend | 3-month Average: Shows smoothed trend"
        )
    
    with col3:
        with st.popover("Settings"):
            st.markdown("### Display Options")
            show_mom_pct = st.checkbox("MoM % Change", value=False)
            highlight_extremes = st.checkbox("Highlight Best/Worst", value=True)
            show_milestones = st.checkbox("Show Milestones", value=True)
    
    # Map preset to features
    show_trend_line = view_preset in ["With Trend Line"]
    show_rolling_avg = view_preset in ["With 3-month Average"]
    
    # -------------------------
    # Prepare data
    # -------------------------
    if breakdown_by == ColumnNames.CATEGORY:
        agg_df = filtered_df.groupby([ColumnNames.MONTH, 'month_Str', ColumnNames.CATEGORY], as_index=False)[ColumnNames.AMOUNT].sum()
        color_column = ColumnNames.CATEGORY
    elif breakdown_by == ColumnNames.ACCOUNT_TYPE:
        agg_df = filtered_df.groupby([ColumnNames.MONTH, 'month_Str', ColumnNames.ACCOUNT_TYPE], as_index=False)[ColumnNames.AMOUNT].sum()
        color_column = ColumnNames.ACCOUNT_TYPE
    else:  # Both
        agg_df = filtered_df.copy()
        agg_df['Group'] = agg_df[ColumnNames.ACCOUNT_TYPE] + ' - ' + agg_df[ColumnNames.CATEGORY]
        agg_df = agg_df.groupby([ColumnNames.MONTH, 'month_Str', 'Group'], as_index=False)[ColumnNames.AMOUNT].sum()
        color_column = 'Group'
    
    # Calculate MoM % change
    totals_df['MoM_Pct'] = totals_df[ColumnNames.AMOUNT].pct_change() * 100
    totals_df['MoM_Pct_Text'] = totals_df['MoM_Pct'].apply(
        lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%" if pd.notna(x) else ""
    )
    totals_df['MoM_Color'] = totals_df['MoM_Pct'].apply(
        lambda x: 'green' if x >= 0 else 'red' if pd.notna(x) else 'gray'
    )
    
    # Calculate rolling average
    if show_rolling_avg and len(totals_df) >= 3:
        totals_df['Rolling_Avg'] = totals_df[ColumnNames.AMOUNT].rolling(window=3, min_periods=1).mean()
    
    # -------------------------
    # Create Chart
    # -------------------------
    fig = px.bar(
        agg_df,
        x=ColumnNames.MONTH,
        y=ColumnNames.AMOUNT,
        color=color_column,
        text=None,
        barmode='stack',
        hover_data={ColumnNames.MONTH: False, ColumnNames.AMOUNT: True, color_column: True},
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    # Add trend line
    if show_trend_line:
        fig.add_trace(
            go.Scatter(
                x=totals_df[ColumnNames.MONTH],
                y=totals_df[ColumnNames.AMOUNT],
                mode='lines+markers',
                name='Total Net Worth',
                line=dict(color='black', width=3),
                marker=dict(size=8, color='black', symbol='diamond'),
                yaxis='y',
                hovertemplate='<b>Total:</b> $%{y:,.0f}<extra></extra>'
            )
        )
    
    # Add rolling average
    if show_rolling_avg and len(totals_df) >= 3:
        fig.add_trace(
            go.Scatter(
                x=totals_df[ColumnNames.MONTH],
                y=totals_df['Rolling_Avg'],
                mode='lines',
                name='3-month Average',
                line=dict(color='orange', width=2, dash='dash'),
                hovertemplate='<b>3-Mo Avg:</b> $%{y:,.0f}<extra></extra>'
            )
        )
    
    # Add milestone markers
    if show_milestones:
        milestones = [100000, 250000, 500000, 750000, 1000000, 1500000, 2000000]
        min_nw = totals_df[ColumnNames.AMOUNT].min()
        max_nw = totals_df[ColumnNames.AMOUNT].max()
        
        for milestone in milestones:
            if min_nw < milestone < max_nw:
                crossed_idx = totals_df[totals_df[ColumnNames.AMOUNT] >= milestone].index[0]
                crossed_date = totals_df.loc[crossed_idx, ColumnNames.MONTH]
                crossed_amount = totals_df.loc[crossed_idx, ColumnNames.AMOUNT]
                
                fig.add_annotation(
                    x=crossed_date,
                    y=crossed_amount,
                    text=f"${milestone/1000:.0f}K",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="gold",
                    ax=20,
                    ay=-40,
                    bgcolor="gold",
                    opacity=0.8,
                    font=dict(size=10, color="black")
                )
    
    # Highlight extremes
    if highlight_extremes and len(totals_df) >= 2:
        best_idx = totals_df[ColumnNames.AMOUNT].idxmax()
        worst_idx = totals_df[ColumnNames.AMOUNT].idxmin()
        
        fig.add_annotation(
            x=totals_df.loc[best_idx, ColumnNames.MONTH],
            y=totals_df.loc[best_idx, ColumnNames.AMOUNT],
            text=f"Best<br>${totals_df.loc[best_idx, ColumnNames.AMOUNT]:,.0f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-50,
            bgcolor="lightgreen",
            opacity=0.8
        )
        
        fig.add_annotation(
            x=totals_df.loc[worst_idx, ColumnNames.MONTH],
            y=totals_df.loc[worst_idx, ColumnNames.AMOUNT],
            text=f"Lowest<br>${totals_df.loc[worst_idx, ColumnNames.AMOUNT]:,.0f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=50,
            bgcolor="lightcoral",
            opacity=0.8
        )
    
    # Add total labels
    fig.add_trace(
        go.Scatter(
            x=totals_df[ColumnNames.MONTH],
            y=totals_df[ColumnNames.AMOUNT],
            text=totals_df[ColumnNames.AMOUNT].apply(lambda x: round_to_k(x)),
            textposition='top center',
            mode='text',
            showlegend=False,
            textfont=dict(size=14, color='black', family="Arial Black"),
            name='Total amount'
        )
    )
    
    # Add MoM % change
    if show_mom_pct:
        fig.add_trace(
            go.Scatter(
                x=totals_df[ColumnNames.MONTH],
                y=totals_df[ColumnNames.AMOUNT] * 1.15,
                text=totals_df['MoM_Pct_Text'],
                textposition='middle center',
                mode='text',
                showlegend=False,
                textfont=dict(size=11, color=totals_df['MoM_Color'], family="Arial"),
                name='MoM Change'
            )
        )
    
    # Layout
    fig.update_layout(
        title="Net Worth Over Time - Detailed View",
        xaxis=dict(
            tickvals=totals_df[ColumnNames.MONTH], 
            ticktext=totals_df['month_Str'], 
            title=ColumnNames.MONTH, 
            tickangle=90
        ),
        yaxis=dict(title='amount ($)', tickprefix='$', tickformat=',.0f'),
        legend_title=breakdown_by,
        hovermode="x unified",
        height=700
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # -------------------------
    # Chart Download
    # -------------------------
    buffer = io.StringIO()
    fig.write_html(buffer, full_html=False)
    buffer.seek(0)
    
    st.download_button(
        label="Download Chart as HTML",
        data=buffer.getvalue(),
        file_name="net_worth_over_time.html",
        mime="text/html"
    )