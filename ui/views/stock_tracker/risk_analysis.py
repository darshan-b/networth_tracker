"""Risk analysis tab for portfolio analysis.

This module provides risk metrics including drawdown and correlation analysis.
"""

from typing import List

import streamlit as st
import pandas as pd

from config import ChartConfig
from data.calculations import aggregate_portfolio_daily
from ui.charts import create_drawdown_chart, create_correlation_heatmap
from ui.components.surfaces import inject_surface_styles, render_accent_pills, render_section_intro


def _aggregate_symbol_history(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Aggregate one clean daily symbol series across brokerages/accounts."""
    symbol_data = df[df['ticker'] == symbol].copy()
    if symbol_data.empty:
        return symbol_data

    return (
        symbol_data.groupby('Date', as_index=False)
        .agg({
            'Last Close': 'mean',
            'Current Value': 'sum',
        })
        .sort_values('Date')
        .reset_index(drop=True)
    )


def render(historical_df: pd.DataFrame, selected_symbols: List[str]) -> None:
    """Render the risk analysis tab.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
        selected_symbols: List of symbols to analyze
    """
    try:
        inject_surface_styles()
        render_section_intro(
            "Risk Analysis",
            "Measure volatility, drawdown, correlation, and beta using daily symbol series that remain stable when the same ticker appears in multiple brokerages.",
        )
        
        if historical_df.empty:
            st.warning("No historical data available for selected filters.")
            return
        
        if not selected_symbols or len(selected_symbols) == 0:
            st.info("No symbols selected. Please select accounts with positions.")
            return
        
        # Display risk summary metrics
        _render_risk_summary(historical_df, selected_symbols)
        
        # Display charts
        col1, col2 = st.columns(2)
        
        with col1:
            render_section_intro(
                "Portfolio Drawdown",
                "Track how far the filtered portfolio fell from prior peaks during the selected period.",
            )
            _render_drawdown_analysis(historical_df)
        
        with col2:
            render_section_intro(
                "Asset Correlation",
                "Spot symbols that move together and identify where diversification is thin.",
            )
            _render_correlation_analysis(historical_df, selected_symbols)
        
        # Display risk breakdown table
        render_section_intro(
            "Risk Metrics by Symbol",
            "Compare volatility, downside, drawdown, and beta at the symbol level.",
        )
        _render_risk_table(historical_df, selected_symbols)
        
    except Exception as e:
        st.error(f"Error rendering risk analysis: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_risk_summary(df: pd.DataFrame, symbols: List[str]) -> None:
    """Render summary risk metrics.
    
    Args:
        df: Historical DataFrame
        symbols: List of symbols
    """
    # Calculate portfolio-level metrics
    portfolio_daily = aggregate_portfolio_daily(df)
    
    if len(portfolio_daily) < 2:
        st.info("Insufficient data for risk analysis.")
        return
    
    # Calculate volatility
    daily_returns = portfolio_daily['Current Value'].pct_change().dropna()
    volatility = daily_returns.std() * 100
    annualized_volatility = volatility * (252 ** 0.5)  # Assuming 252 trading days
    
    # Calculate max drawdown
    cumulative = portfolio_daily['Current Value'] / portfolio_daily['Current Value'].iloc[0]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    # Calculate Value at Risk (95% confidence)
    var_95 = daily_returns.quantile(0.05) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Daily Volatility", f"{volatility:.2f}%")
    
    with col2:
        st.metric("Annualized Volatility", f"{annualized_volatility:.2f}%")
    
    with col3:
        st.metric("Max Drawdown", f"{max_drawdown:.2f}%")
    
    with col4:
        st.metric("VaR (95%)", f"{var_95:.2f}%")
    
    st.divider()


def _render_drawdown_analysis(df: pd.DataFrame) -> None:
    """Render drawdown chart and analysis.
    
    Args:
        df: Historical DataFrame
    """
    try:
        portfolio_daily = aggregate_portfolio_daily(df)
        
        if len(portfolio_daily) < 2:
            st.info("Insufficient data for drawdown analysis.")
            return
        
        fig = create_drawdown_chart(portfolio_daily)
        st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)
        
        # Calculate drawdown statistics
        cumulative = portfolio_daily['Current Value'] / portfolio_daily['Current Value'].iloc[0]
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        
        max_dd = drawdown.min()
        avg_dd = drawdown[drawdown < 0].mean() if len(drawdown[drawdown < 0]) > 0 else 0
        
        st.caption(
            f"**Max Drawdown:** {max_dd:.2f}% | "
            f"**Avg Drawdown:** {avg_dd:.2f}%"
        )
        
    except Exception as e:
        st.error(f"Error creating drawdown chart: {str(e)}")


def _render_correlation_analysis(df: pd.DataFrame, symbols: List[str]) -> None:
    """Render correlation heatmap and analysis.
    
    Args:
        df: Historical DataFrame
        symbols: List of symbols
    """
    try:
        if len(symbols) < 2:
            st.info("Select at least 2 symbols to view correlation matrix.")
            return
        
        fig = create_correlation_heatmap(df)
        st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)
        
        st.caption(
            "**Correlation Matrix:** Shows how assets move together. "
            "Values close to 1 indicate positive correlation, "
            "close to -1 indicate negative correlation, "
            "and close to 0 indicate no correlation."
        )
        
    except Exception as e:
        st.error(f"Error creating correlation matrix: {str(e)}")


def _render_risk_table(df: pd.DataFrame, symbols: List[str]) -> None:
    """Render detailed risk metrics table by symbol.
    
    Args:
        df: Historical DataFrame
        symbols: List of symbols
    """
    risk_data = []
    
    for symbol in symbols:
        symbol_data = _aggregate_symbol_history(df, symbol)
        
        if len(symbol_data) < 2:
            continue

        symbol_data['Date'] = pd.to_datetime(symbol_data['Date'], errors='coerce')
        symbol_data = symbol_data.dropna(subset=['Date'])
        if len(symbol_data) < 2:
            continue
        
        # Calculate metrics
        returns = (
            symbol_data.set_index('Date')['Last Close']
            .pct_change()
            .dropna()
        )
        
        if len(returns) == 0:
            continue
        
        volatility = returns.std() * 100
        annualized_vol = volatility * (252 ** 0.5)
        
        # Drawdown
        prices = symbol_data['Last Close']
        cumulative = prices / prices.iloc[0]
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min()
        
        # Downside deviation
        downside_returns = returns[returns < 0]
        downside_dev = downside_returns.std() * 100 if len(downside_returns) > 0 else 0
        
        # Beta (relative to equal-weighted portfolio)
        portfolio_returns = (
            df.assign(Date=pd.to_datetime(df['Date'], errors='coerce'))
            .dropna(subset=['Date'])
            .groupby('Date')['Current Value']
            .sum()
            .pct_change()
            .dropna()
        )
        
        # Align dates for beta calculation
        aligned_returns = pd.concat(
            [
                returns.rename('symbol'),
                portfolio_returns.rename('portfolio'),
            ],
            axis=1,
        ).dropna()
        
        if len(aligned_returns) > 0:
            covariance = aligned_returns['symbol'].cov(aligned_returns['portfolio'])
            portfolio_variance = aligned_returns['portfolio'].var()
            beta = covariance / portfolio_variance if portfolio_variance > 0 else 1.0
        else:
            beta = 1.0
        
        risk_data.append({
            'ticker': symbol,
            'Volatility %': volatility,
            'Annual Volatility %': annualized_vol,
            'Max Drawdown %': max_drawdown,
            'Downside Dev %': downside_dev,
            'Beta': beta
        })
    
    if not risk_data:
        st.info("Insufficient data for risk metrics calculation.")
        return
    
    risk_df = pd.DataFrame(risk_data)
    
    # Display formatted table
    st.dataframe(
        risk_df.style.format({
            'Volatility %': '{:.2f}%',
            'Annual Volatility %': '{:.2f}%',
            'Max Drawdown %': '{:.2f}%',
            'Downside Dev %': '{:.2f}%',
            'Beta': '{:.2f}'
        }).background_gradient(
            subset=['Volatility %'],
            cmap='YlOrRd'
        ),
        width="stretch",
        hide_index=True
    )
    
    st.caption(
        "**Volatility:** Standard deviation of returns. Higher = more risk.\n\n"
        "**Max Drawdown:** Largest peak-to-trough decline. Lower = better.\n\n"
        "**Downside Deviation:** Volatility of negative returns only.\n\n"
        "**Beta:** Sensitivity to portfolio movements. >1 = more volatile than portfolio."
    )
    render_accent_pills(
        [
            ("Symbols", str(len(risk_df))),
            ("Highest Beta", f"{risk_df['Beta'].max():.2f}"),
            ("Deepest Drawdown", f"{risk_df['Max Drawdown %'].min():.2f}%"),
        ]
    )
