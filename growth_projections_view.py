# ============================================================================
# FILE: growth_projections_view.py
# ============================================================================
"""Growth Projections view - Goal tracking and investment calculator."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def calculate_months_to_goal(current_value, goal_amount, monthly_contribution, annual_return_rate, compound_freq='monthly'):
    """
    Calculate the number of months needed to reach a financial goal with compound interest.
    
    Args:
        current_value: Starting net worth
        goal_amount: Target net worth
        monthly_contribution: Monthly additional contribution
        annual_return_rate: Annual return rate as percentage (e.g., 7 for 7%)
        compound_freq: 'monthly' or 'annually'
        
    Returns:
        Number of months to reach goal, or None if goal is unreachable
    """
    if goal_amount <= current_value:
        return 0
    
    if annual_return_rate == 0 and monthly_contribution == 0:
        return None
    
    annual_rate = annual_return_rate / 100
    
    if compound_freq == 'monthly':
        monthly_rate = annual_rate / 12
    else:
        monthly_rate = (1 + annual_rate) ** (1/12) - 1
    
    if monthly_rate == 0:
        if monthly_contribution > 0:
            return (goal_amount - current_value) / monthly_contribution
        return None
    
    if monthly_contribution == 0:
        if current_value <= 0:
            return None
        months = np.log(goal_amount / current_value) / np.log(1 + monthly_rate)
    else:
        months = 0
        balance = current_value
        max_months = 1200
        
        while balance < goal_amount and months < max_months:
            balance = balance * (1 + monthly_rate) + monthly_contribution
            months += 1
        
        if months >= max_months:
            return None
    
    return months


def format_time_to_goal(months):
    """Format months into years and months."""
    if months is None:
        return "Goal unreachable"
    
    if months == 0:
        return "Goal achieved!"
    
    years = int(months // 12)
    remaining_months = int(months % 12)
    
    if years == 0:
        return f"{remaining_months} month{'s' if remaining_months != 1 else ''}"
    elif remaining_months == 0:
        return f"{years} year{'s' if years != 1 else ''}"
    else:
        return f"{years} year{'s' if years != 1 else ''} and {remaining_months} month{'s' if remaining_months != 1 else ''}"


def generate_projection_data(current_value, goal_amount, monthly_contribution, annual_return_rate, compound_freq, max_months=600):
    """Generate month-by-month projection data for visualization."""
    annual_rate = annual_return_rate / 100
    
    if compound_freq == 'monthly':
        monthly_rate = annual_rate / 12
    else:
        monthly_rate = (1 + annual_rate) ** (1/12) - 1
    
    months = []
    balances = []
    contributions_cumulative = []
    growth_cumulative = []
    
    balance = current_value
    total_contributions = 0
    
    for month in range(max_months + 1):
        months.append(month)
        balances.append(balance)
        contributions_cumulative.append(total_contributions)
        growth_cumulative.append(balance - current_value - total_contributions)
        
        if balance >= goal_amount:
            break
        
        balance = balance * (1 + monthly_rate) + monthly_contribution
        total_contributions += monthly_contribution
    
    return pd.DataFrame({
        'Month': months,
        'Balance': balances,
        'Contributions': contributions_cumulative,
        'Growth': growth_cumulative
    })


def create_breakdown_chart(projection_df, current_value):
    """Create stacked area chart showing contribution breakdown."""
    fig = go.Figure()
    
    # Starting balance (constant)
    fig.add_trace(
        go.Scatter(
            x=projection_df['Month'],
            y=[current_value] * len(projection_df),
            name='Starting Balance',
            mode='lines',
            stackgroup='one',
            line=dict(width=0.5, color='#2ca02c'),
            fillcolor='#2ca02c',
            hovertemplate='Starting: $%{y:,.0f}<extra></extra>'
        )
    )
    
    # Contributions
    fig.add_trace(
        go.Scatter(
            x=projection_df['Month'],
            y=projection_df['Contributions'],
            name='Contributions',
            mode='lines',
            stackgroup='one',
            line=dict(width=0.5, color='#ff7f0e'),
            fillcolor='#ff7f0e',
            hovertemplate='Contributions: $%{y:,.0f}<extra></extra>'
        )
    )
    
    # Growth
    fig.add_trace(
        go.Scatter(
            x=projection_df['Month'],
            y=projection_df['Growth'],
            name='Investment Growth',
            mode='lines',
            stackgroup='one',
            line=dict(width=0.5, color='#1f77b4'),
            fillcolor='#1f77b4',
            hovertemplate='Growth: $%{y:,.0f}<extra></extra>'
        )
    )
    
    fig.update_layout(
        title="Balance Breakdown Over Time",
        xaxis_title="Months from Now",
        yaxis_title="Amount ($)",
        template='plotly_white',
        height=400,
        hovermode='x unified'
    )
    
    fig.update_yaxes(tickprefix='$', tickformat=',.0f')
    
    return fig


def show_growth_projections(filtered_df):
    """
    Main function to display the growth projections tab.
    
    Args:
        filtered_df: Filtered dataset based on user selections
    """
    st.header("Growth Projections & Goal Planning")
    
    # Calculate current net worth
    totals_df = filtered_df.groupby(['Month', 'Month_Str'], as_index=False)['Amount'].sum()
    
    if totals_df.empty:
        st.warning("No data available. Please adjust your filters.")
        return
    
    current_nw = totals_df.iloc[-1]['Amount']
    
    # Calculate historical metrics
    if len(totals_df) >= 2:
        first_nw = totals_df.iloc[0]['Amount']
        total_change = current_nw - first_nw
        avg_monthly_growth = total_change / len(totals_df) if len(totals_df) > 0 else 0
        
        # Display current status
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Current Net Worth", f"${current_nw:,.0f}")
        
        with col2:
            st.metric("Historical Avg Growth", f"${avg_monthly_growth:,.0f}/mo")
        
        with col3:
            months_tracked = len(totals_df)
            st.metric("Months Tracked", months_tracked)
    else:
        avg_monthly_growth = 0
        st.warning("Need at least 2 months of data for projections.")
        return
    
    st.divider()
    
    # Goal input section
    st.subheader("Set Your Goal")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        goal_amount = st.number_input(
            "Target Net Worth ($)",
            min_value=0,
            value=max(1000000, int(current_nw * 1.5)),
            step=10000,
            format="%d",
            help="Your target net worth goal"
        )
    
    with col2:
        if goal_amount <= current_nw:
            st.success("Goal Already Achieved!")
            st.balloons()
            return
        
        remaining = goal_amount - current_nw
        st.metric("Remaining", f"${remaining:,.0f}")
    
    st.divider()
    
    # Investment parameters
    st.subheader("Investment Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        monthly_contribution = st.number_input(
            "Monthly Contribution ($)",
            min_value=0,
            value=0,
            step=100,
            help="Additional amount you'll invest each month"
        )
    
    with col2:
        annual_return = st.number_input(
            "Expected Annual Return (%)",
            min_value=0.0,
            max_value=50.0,
            value=7.0,
            step=0.5,
            help="Expected average annual return rate (e.g., 7% for stock market average)"
        )
    
    with col3:
        compound_freq = st.selectbox(
            "Compounding Frequency",
            options=['monthly', 'annually'],
            index=0,
            help="How often returns are compounded"
        )
    
    # Calculate projections
    months_to_goal = calculate_months_to_goal(
        current_nw,
        goal_amount,
        monthly_contribution,
        annual_return,
        compound_freq
    )
    
    st.divider()
    
    # Display results
    if months_to_goal is None:
        st.error("Goal is not reachable with current parameters.")
        st.info("Try increasing monthly contributions or expected returns.")
        return
    
    # Key results
    st.subheader("Projection Results")
    
    time_str = format_time_to_goal(months_to_goal)
    total_contributions = monthly_contribution * months_to_goal
    total_growth = goal_amount - current_nw - total_contributions
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Time to Goal", time_str)
    
    with col2:
        st.metric("Total Contributions", f"${total_contributions:,.0f}")
    
    with col3:
        st.metric("Investment Growth", f"${total_growth:,.0f}")
    
    with col4:
        growth_pct = (total_growth / (current_nw + total_contributions) * 100) if (current_nw + total_contributions) > 0 else 0
        st.metric("Growth Rate", f"{growth_pct:.1f}%")
    
    st.divider()
    
    # Generate projection data
    projection_df = generate_projection_data(
        current_nw,
        goal_amount,
        monthly_contribution,
        annual_return,
        compound_freq,
        max_months=int(months_to_goal)
    )
    
    # Create visualizations
    st.subheader("Visual Projections")
    
    # Breakdown chart
    fig_breakdown = create_breakdown_chart(projection_df, current_nw)
    st.plotly_chart(fig_breakdown, use_container_width=True)
    
    st.divider()
    
    # Detailed projection table
    with st.expander("View Detailed Projection Table"):
        # Sample key milestones
        if len(projection_df) > 12:
            # Show quarterly snapshots
            milestone_rows = projection_df[projection_df['Month'] % 3 == 0].copy()
        else:
            milestone_rows = projection_df.copy()
        
        # Format for display
        display_df = milestone_rows.copy()
        display_df['Balance'] = display_df['Balance'].apply(lambda x: f"${x:,.0f}")
        display_df['Contributions'] = display_df['Contributions'].apply(lambda x: f"${x:,.0f}")
        display_df['Growth'] = display_df['Growth'].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Comparison with historical growth
    if avg_monthly_growth > 0:
        st.divider()
        st.subheader("Comparison with Historical Performance")
        
        historical_months = (goal_amount - current_nw) / avg_monthly_growth
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**With Investment Strategy**")
            st.write(f"Time to Goal: {time_str}")
            st.write(f"Monthly Contribution: ${monthly_contribution:,.0f}")
            st.write(f"Expected Return: {annual_return}%")
        
        with col2:
            st.markdown("**Based on Historical Growth**")
            st.write(f"Time to Goal: {format_time_to_goal(historical_months)}")
            st.write(f"Avg Historical Growth: ${avg_monthly_growth:,.0f}/mo")
            st.write(f"Difference: {abs(months_to_goal - historical_months):.0f} months")
    
    # Assumptions and disclaimers
    st.divider()
    st.caption(f"""
    **Assumptions:** Starting balance: ${current_nw:,.0f} | Monthly contribution: ${monthly_contribution:,.0f} | 
    Annual return: {annual_return}% ({compound_freq} compounding)
    """)
    
    st.info("Note: These projections are based on assumed returns and contributions. Actual results will vary based on market performance and your actual saving/investment behavior. This is for planning purposes only and should not be considered financial advice.")
