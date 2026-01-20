"""Performance tab for portfolio analysis.

This module provides performance comparison and analysis across symbols.
"""

from typing import List

import streamlit as st
import pandas as pd

from ui.charts import create_performance_comparison


def render(historical_df: pd.DataFrame, selected_symbols: List[str]) -> None:
    """Render the performance analysis tab.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
        selected_symbols: List of symbols to analyze
    """
    try:
        st.header("Performance Analysis")
        
        if historical_df.empty:
            st.warning("No historical data available for selected filters.")
            return
        
        if not selected_symbols or len(selected_symbols) == 0:
            st.info("No symbols selected. Please select accounts with positions.")
            return
        
        # Display performance comparison chart
        st.subheader("Normalized Performance Comparison")
        _render_performance_chart(historical_df, selected_symbols)
        
        # Display individual performance metrics
        st.subheader("Individual Stock Performance")
        _render_performance_table(historical_df, selected_symbols)
        
        # Display performance statistics
        st.subheader("Performance Statistics")
        _render_performance_statistics(historical_df, selected_symbols)
        
    except Exception as e:
        st.error(f"Error rendering performance analysis: {str(e)}")
        with st.expander("Error Details"):
            st.exception(e)


def _render_performance_chart(df: pd.DataFrame, symbols: List[str]) -> None:
    """Render performance comparison chart.
    
    Args:
        df: Historical DataFrame
        symbols: List of symbols to compare
    """
    try:
        if len(symbols) == 0:
            st.info("Select at least one symbol to view performance comparison.")
            return
        
        fig = create_performance_comparison(df, symbols)
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption(
            "**Note:** All values are normalized to 100 at the start of the period "
            "for easy comparison of relative performance."
        )
    except Exception as e:
        st.error(f"Error creating performance chart: {str(e)}")


def _render_performance_table(df: pd.DataFrame, symbols: List[str]) -> None:
    """Render individual stock performance table.
    
    Args:
        df: Historical DataFrame
        symbols: List of symbols to analyze
    """
    perf_data = []
    
    for symbol in symbols:
        symbol_data = df[df['ticker'] == symbol].sort_values('Date')
        
        if len(symbol_data) < 2:
            continue
        
        # Calculate returns
        start_price = symbol_data['Last Close'].iloc[0]
        end_price = symbol_data['Last Close'].iloc[-1]
        start_value = symbol_data['Current Value'].iloc[0]
        end_value = symbol_data['Current Value'].iloc[-1]
        start_cost = symbol_data['Cost Basis'].iloc[0]
        end_cost = symbol_data['Cost Basis'].iloc[-1]
        
        price_return = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0
        value_return = ((end_value - start_value) / start_value) * 100 if start_value > 0 else 0
        total_return = ((end_value - end_cost) / end_cost) * 100 if end_cost > 0 else 0
        
        # Calculate volatility (standard deviation of daily returns)
        daily_returns = symbol_data['Last Close'].pct_change().dropna()
        volatility = daily_returns.std() * 100 if len(daily_returns) > 0 else 0
        
        perf_data.append({
            'ticker': symbol,
            'Start Price': start_price,
            'End Price': end_price,
            'Price Return %': price_return,
            'Value Return %': value_return,
            'Total Return %': total_return,
            'Volatility %': volatility
        })
    
    if not perf_data:
        st.info("Insufficient data for performance analysis.")
        return
    
    perf_df = pd.DataFrame(perf_data)
    
    # Display formatted table
    st.dataframe(
        perf_df.style.format({
            'Start Price': '${:.2f}',
            'End Price': '${:.2f}',
            'Price Return %': '{:.2f}%',
            'Value Return %': '{:.2f}%',
            'Total Return %': '{:.2f}%',
            'Volatility %': '{:.2f}%'
        }).background_gradient(
            subset=['Total Return %'],
            cmap='RdYlGn',
            vmin=-20,
            vmax=20
        ),
        use_container_width=True,
        hide_index=True
    )


def _render_performance_statistics(df: pd.DataFrame, symbols: List[str]) -> None:
    """Render performance statistics summary.
    
    Args:
        df: Historical DataFrame
        symbols: List of symbols to analyze
    """
    stats = []
    
    for symbol in symbols:
        symbol_data = df[df['ticker'] == symbol].sort_values('Date')
        
        if len(symbol_data) < 2:
            continue
        
        # Calculate various metrics
        returns = symbol_data['Last Close'].pct_change().dropna()
        
        if len(returns) == 0:
            continue
        
        # Basic statistics
        avg_return = returns.mean() * 100
        std_return = returns.std() * 100
        min_return = returns.min() * 100
        max_return = returns.max() * 100
        
        # Sharpe ratio (simplified, assuming risk-free rate = 0)
        sharpe = (avg_return / std_return) if std_return > 0 else 0
        
        stats.append({
            'ticker': symbol,
            'Avg Daily Return %': avg_return,
            'Std Dev %': std_return,
            'Min Return %': min_return,
            'Max Return %': max_return,
            'Sharpe Ratio': sharpe
        })
    
    if not stats:
        st.info("Insufficient data for statistics calculation.")
        return
    
    stats_df = pd.DataFrame(stats)
    
    # Display formatted table
    st.dataframe(
        stats_df.style.format({
            'Avg Daily Return %': '{:.3f}%',
            'Std Dev %': '{:.3f}%',
            'Min Return %': '{:.2f}%',
            'Max Return %': '{:.2f}%',
            'Sharpe Ratio': '{:.3f}'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.caption(
        "**Sharpe Ratio:** Higher is better. Measures risk-adjusted returns. "
        "Simplified calculation assumes risk-free rate = 0."
    )