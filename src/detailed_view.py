import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.express as px
import plotly.graph_objects as go


def round_to_k(amount):
    if amount >= 1000:
        return f"{amount/1000:.1f}k"  # Round to 1 decimal place and add 'k'
    else:
        return f"{amount:.0f}"



def show_detailed_view(filtered_df):

    st.header("Net Worth Over Time")

    # -------------------------
    # Summary Statistics with Insights
    # -------------------------
    st.subheader("Quick Stats")
    
    totals_df = filtered_df.groupby(['Month', 'Month_Str'], as_index=False)['Amount'].sum()
    
    if len(totals_df) >= 2:
        current_nw = totals_df.iloc[-1]['Amount']
        previous_nw = totals_df.iloc[-2]['Amount']
        first_nw = totals_df.iloc[0]['Amount']
        
        mom_change = current_nw - previous_nw
        mom_pct = (mom_change / abs(previous_nw)) * 100 if previous_nw != 0 else 0
        
        total_change = current_nw - first_nw
        total_pct = (total_change / abs(first_nw)) * 100 if first_nw != 0 else 0
        
        # Calculate average monthly growth
        avg_monthly_growth = total_change / len(totals_df) if len(totals_df) > 0 else 0
        
        # Calculate growth velocity (is growth accelerating?)
        if len(totals_df) >= 3:
            prev_period_change = totals_df.iloc[-2]['Amount'] - totals_df.iloc[-3]['Amount']
            velocity = mom_change - prev_period_change
            velocity_emoji = "🚀" if velocity > 0 else "🐌" if velocity < 0 else "➡️"
            velocity_text = f"{velocity_emoji} {'Accelerating' if velocity > 0 else 'Decelerating' if velocity < 0 else 'Steady'}"
        else:
            velocity_text = "N/A"
        
        # Find best and worst months
        best_idx = totals_df['Amount'].idxmax()
        worst_idx = totals_df['Amount'].idxmin()
        best_month = totals_df.loc[best_idx, 'Month_Str']
        worst_month = totals_df.loc[worst_idx, 'Month_Str']
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Current Net Worth", f"${current_nw:,.0f}", 
                     f"{mom_change:,.0f} ({mom_pct:+.1f}%)")
        with col2:
            st.metric("Total Growth", f"${total_change:,.0f}", f"{total_pct:+.1f}%")
        with col3:
            st.metric("Months Tracked", len(totals_df))
        with col4:
            st.metric("Growth Momentum", velocity_text)
        with col5:
            st.metric("Avg Monthly Growth", f"${avg_monthly_growth:,.0f}")
    
    st.divider()
    
    # -------------------------
    # Streamlined Controls - Single Row
    # -------------------------
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        breakdown_by = st.selectbox("Breakdown By:", ["Category", "Account Type", "Both"], key="breakdown")
    
    with col2:
        # View preset options
        view_preset = st.selectbox(
            "Chart View:", 
            ["Standard", "With Trend Line", "With 3-Month Average"],
            index=1,  # Default to "With Trend Line"
            help="Standard: Basic stacked bars | Trend Line: Adds net worth trend | 3-Month Average: Shows smoothed trend"
        )
    
    with col3:
        # Advanced settings in popover
        with st.popover("⚙️ Settings"):
            st.markdown("### Display Options")
            show_mom_pct = st.checkbox("MoM % Change", value=False)
            highlight_extremes = st.checkbox("Highlight Best/Worst", value=True)
            show_milestones = st.checkbox("Show Milestones", value=True)
            
            st.divider()
            st.markdown("### Forecasting")
            show_forecast = st.checkbox("6-Month Forecast", value=False)
            
            st.divider()
            st.markdown("### Goal Tracking")
            enable_goal = st.checkbox("Enable Goal Line", value=False)
            if enable_goal:
                goal_amount = st.number_input("Goal Amount ($)", min_value=0, value=1000000, step=50000)
            else:
                goal_amount = None
    
    # Map preset to features
    show_trend_line = view_preset in ["With Trend Line"]
    show_rolling_avg = view_preset in ["With 3-Month Average"]
    
    # -------------------------
    # Prepare data based on breakdown selection
    # -------------------------
    if breakdown_by == "Category":
        agg_df = filtered_df.groupby(['Month', 'Month_Str', 'Category'], as_index=False)['Amount'].sum()
        color_column = 'Category'
    elif breakdown_by == "Account Type":
        agg_df = filtered_df.groupby(['Month', 'Month_Str', 'Account Type'], as_index=False)['Amount'].sum()
        color_column = 'Account Type'
    else:  # Both
        agg_df = filtered_df.copy()
        agg_df['Group'] = agg_df['Account Type'] + ' - ' + agg_df['Category']
        agg_df = agg_df.groupby(['Month', 'Month_Str', 'Group'], as_index=False)['Amount'].sum()
        color_column = 'Group'
    
    totals_df = filtered_df.groupby(['Month', 'Month_Str'], as_index=False)['Amount'].sum()
    
    # Calculate MoM % change
    totals_df['MoM_Pct'] = totals_df['Amount'].pct_change() * 100
    totals_df['MoM_Pct_Text'] = totals_df['MoM_Pct'].apply(
        lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%" if pd.notna(x) else ""
    )
    totals_df['MoM_Color'] = totals_df['MoM_Pct'].apply(
        lambda x: 'green' if x >= 0 else 'red' if pd.notna(x) else 'gray'
    )
    
    # Calculate rolling average
    if show_rolling_avg and len(totals_df) >= 3:
        totals_df['Rolling_Avg'] = totals_df['Amount'].rolling(window=3, min_periods=1).mean()
    
    # -------------------------
    # Create Chart
    # -------------------------
    fig = px.bar(
        agg_df,
        x='Month',
        y='Amount',
        color=color_column,
        text=None,
        barmode='stack',
        hover_data={'Month': False, 'Amount': True, color_column: True},
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    # Add trend line if selected
    if show_trend_line:
        fig.add_trace(
            go.Scatter(
                x=totals_df['Month'],
                y=totals_df['Amount'],
                mode='lines+markers',
                name='Total Net Worth',
                line=dict(color='black', width=3),
                marker=dict(size=8, color='black', symbol='diamond'),
                yaxis='y',
                hovertemplate='<b>Total:</b> $%{y:,.0f}<extra></extra>'
            )
        )
    
    # Add rolling average if selected
    if show_rolling_avg and len(totals_df) >= 3:
        fig.add_trace(
            go.Scatter(
                x=totals_df['Month'],
                y=totals_df['Rolling_Avg'],
                mode='lines',
                name='3-Month Average',
                line=dict(color='orange', width=2, dash='dash'),
                hovertemplate='<b>3-Mo Avg:</b> $%{y:,.0f}<extra></extra>'
            )
        )
    
    # Add forecast if selected
    if show_forecast and len(totals_df) >= 3:
        # Simple linear regression for forecast
        from scipy import stats
        x_vals = np.arange(len(totals_df))
        y_vals = totals_df['Amount'].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_vals, y_vals)
        
        # Project 6 months ahead
        forecast_months = 6
        forecast_x = np.arange(len(totals_df), len(totals_df) + forecast_months)
        forecast_y = slope * forecast_x + intercept
        
        # Create forecast dates
        last_date = totals_df['Month'].max()
        forecast_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=forecast_months, freq='MS')
        
        fig.add_trace(
            go.Scatter(
                x=forecast_dates,
                y=forecast_y,
                mode='lines+markers',
                name='6-Month Forecast',
                line=dict(color='purple', width=2, dash='dot'),
                marker=dict(size=6, symbol='x'),
                hovertemplate='<b>Projected:</b> $%{y:,.0f}<extra></extra>'
            )
        )
    
    # Add goal line if enabled
    if enable_goal and goal_amount:
        fig.add_hline(
            y=goal_amount,
            line_dash="dash",
            line_color="blue",
            annotation_text=f"Goal: ${goal_amount:,.0f}",
            annotation_position="right"
        )
    
    # Add milestone markers if selected
    if show_milestones:
        milestones = [100000, 250000, 500000, 750000, 1000000, 1500000, 2000000]
        min_nw = totals_df['Amount'].min()
        max_nw = totals_df['Amount'].max()
        
        for milestone in milestones:
            if min_nw < milestone < max_nw:
                # Find when milestone was crossed
                crossed_idx = totals_df[totals_df['Amount'] >= milestone].index[0]
                crossed_date = totals_df.loc[crossed_idx, 'Month']
                crossed_amount = totals_df.loc[crossed_idx, 'Amount']
                
                fig.add_annotation(
                    x=crossed_date,
                    y=crossed_amount,
                    text=f"🎯 ${milestone/1000:.0f}K",
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
    
    # Highlight best and worst months if selected
    if highlight_extremes and len(totals_df) >= 2:
        best_idx = totals_df['Amount'].idxmax()
        worst_idx = totals_df['Amount'].idxmin()
        
        fig.add_annotation(
            x=totals_df.loc[best_idx, 'Month'],
            y=totals_df.loc[best_idx, 'Amount'],
            text=f"🏆 Best<br>${totals_df.loc[best_idx, 'Amount']:,.0f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-50,
            bgcolor="lightgreen",
            opacity=0.8
        )
        
        fig.add_annotation(
            x=totals_df.loc[worst_idx, 'Month'],
            y=totals_df.loc[worst_idx, 'Amount'],
            text=f"⚠️ Lowest<br>${totals_df.loc[worst_idx, 'Amount']:,.0f}",
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=50,
            bgcolor="lightcoral",
            opacity=0.8
        )
    
    # Add total labels on top
    fig.add_trace(
        go.Scatter(
            x=totals_df['Month'],
            y=totals_df['Amount'],
            text=totals_df['Amount'].apply(lambda x: round_to_k(x)),
            textposition='top center',
            mode='text',
            showlegend=False,
            textfont=dict(size=14, color='black', family="Arial Black"),
            name='Total Amount'
        )
    )
    
    # Add MoM % change if selected
    if show_mom_pct:
        fig.add_trace(
            go.Scatter(
                x=totals_df['Month'],
                y=totals_df['Amount'] * 1.15,  # Position above bars
                text=totals_df['MoM_Pct_Text'],
                textposition='middle center',
                mode='text',
                showlegend=False,
                textfont=dict(size=11, color=totals_df['MoM_Color'], family="Arial"),
                name='MoM Change'
            )
        )
    
    # -------------------------
    # Layout
    # -------------------------
    fig.update_layout(
        title="Net Worth Over Time - Detailed View",
        xaxis=dict(
            tickvals=totals_df['Month'], 
            ticktext=totals_df['Month_Str'], 
            title='Month', 
            tickangle=90
        ),
        yaxis=dict(title='Amount ($)', tickprefix='$', tickformat=',.0f'),
        legend_title=breakdown_by,
        hovermode="x unified",
        height=700
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # -------------------------
    # Insights Panel
    # -------------------------
    with st.expander("📊 Key Insights", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Performance Summary")
            st.write(f"**Best Month:** {best_month} (${totals_df.loc[best_idx, 'Amount']:,.0f})")
            st.write(f"**Lowest Month:** {worst_month} (${totals_df.loc[worst_idx, 'Amount']:,.0f})")
            st.write(f"**Peak to Trough:** ${totals_df.loc[best_idx, 'Amount'] - totals_df.loc[worst_idx, 'Amount']:,.0f}")
            
            if len(totals_df) >= 3:
                volatility = totals_df['Amount'].std()
                st.write(f"**Volatility (Std Dev):** ${volatility:,.0f}")
        
        with col2:
            st.markdown("### Progress Tracking")
            if enable_goal and goal_amount:
                progress = (current_nw / goal_amount) * 100
                remaining = goal_amount - current_nw
                months_to_goal = remaining / avg_monthly_growth if avg_monthly_growth > 0 else float('inf')
                
                st.write(f"**Goal Progress:** {progress:.1f}%")
                st.progress(min(progress / 100, 1.0))
                st.write(f"**Remaining:** ${remaining:,.0f}")
                if months_to_goal != float('inf'):
                    st.write(f"**Est. Time to Goal:** {months_to_goal:.1f} months")
            else:
                st.info("Enable goal tracking in settings ⚙️")
    
    # -------------------------
    # Chart Download
    # -------------------------
    buffer = io.StringIO()
    fig.write_html(buffer, full_html=False)
    buffer.seek(0)
    
    st.download_button(
        label="📊 Download Chart as HTML",
        data=buffer.getvalue(),
        file_name="net_worth_over_time.html",
        mime="text/html"
    )
