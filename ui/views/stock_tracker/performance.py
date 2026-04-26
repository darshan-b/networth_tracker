"""Performance tab for portfolio analysis."""

from typing import List

import pandas as pd
import streamlit as st

from config import ChartConfig
from data.stock_analytics import aggregate_symbol_history, calculate_annualized_return, calculate_return_statistics
from ui.charts import create_performance_comparison
from ui.components.surfaces import inject_surface_styles, render_accent_pills, render_section_intro


def render(historical_df: pd.DataFrame, selected_symbols: List[str]) -> None:
    """Render the performance analysis tab.
    
    Args:
        historical_df: Historical tracking DataFrame (already filtered)
        selected_symbols: List of symbols to analyze
    """
    try:
        inject_surface_styles()
        render_section_intro(
            "Performance Analysis",
            "Compare symbol-level price moves and value growth across the filtered portfolio without cross-broker duplicate-date distortion.",
        )
        
        if historical_df.empty:
            st.warning("No historical data available for selected filters.")
            return
        
        if not selected_symbols or len(selected_symbols) == 0:
            st.info("No symbols selected. Please select accounts with positions.")
            return
        
        # Display performance comparison chart
        render_section_intro(
            "Normalized Comparison",
            "All series are rebased to 100 at the start of the selected window so relative price performance is directly comparable.",
        )
        _render_performance_chart(historical_df, selected_symbols)
        
        # Display individual performance metrics
        render_section_intro(
            "Symbol Performance",
            "Review start/end prices, value growth, total return, and realized volatility by symbol.",
        )
        _render_performance_table(historical_df, selected_symbols)
        
        # Display performance statistics
        render_section_intro(
            "Performance Statistics",
            "Use daily return statistics to compare consistency, downside, and risk-adjusted behavior across symbols.",
        )
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
        st.plotly_chart(fig, config=ChartConfig.STREAMLIT_CONFIG)
        
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
        symbol_data = aggregate_symbol_history(df, symbol)
        
        if len(symbol_data) < 2:
            continue
        
        start_price = symbol_data['Last Close'].iloc[0]
        end_price = symbol_data['Last Close'].iloc[-1]
        start_value = symbol_data['Current Value'].iloc[0]
        end_value = symbol_data['Current Value'].iloc[-1]
        start_cost = symbol_data['Cost Basis'].iloc[0]
        end_cost = symbol_data['Cost Basis'].iloc[-1]

        price_return = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0
        value_return = ((end_value - start_value) / start_value) * 100 if start_value > 0 else 0
        total_return = ((end_value - end_cost) / end_cost) * 100 if end_cost > 0 else 0
        annualized_return = calculate_annualized_return(
            start_price,
            end_price,
            symbol_data['Date'].iloc[0],
            symbol_data['Date'].iloc[-1],
        ) * 100
        stats = calculate_return_statistics(symbol_data['Daily Return'])

        perf_data.append({
            'ticker': symbol,
            'Start Price': start_price,
            'End Price': end_price,
            'Price Return %': price_return,
            'Value Return %': value_return,
            'Annualized Price Return %': annualized_return,
            'Total Return %': total_return,
            'Volatility %': stats['annualized_volatility'] * 100,
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
            'Annualized Price Return %': '{:.2f}%',
            'Total Return %': '{:.2f}%',
            'Volatility %': '{:.2f}%'
        }).background_gradient(
            subset=['Total Return %'],
            cmap='RdYlGn',
            vmin=-20,
            vmax=20
        ),
        width="stretch",
        hide_index=True
    )


def _render_performance_statistics(df: pd.DataFrame, symbols: List[str]) -> None:
    """Render performance statistics summary.
    
    Args:
        df: Historical DataFrame
        symbols: List of symbols to analyze
    """
    stat_rows = []
    
    for symbol in symbols:
        symbol_data = aggregate_symbol_history(df, symbol)
        
        if len(symbol_data) < 2:
            continue
        
        symbol_stats = calculate_return_statistics(symbol_data['Daily Return'])
        if (
            symbol_stats['annualized_volatility'] == 0
            and symbol_stats['best_day'] == 0
            and symbol_stats['worst_day'] == 0
        ):
            continue

        stat_rows.append({
            'ticker': symbol,
            'Avg Daily Return %': symbol_stats['avg_daily_return'] * 100,
            'Annual Volatility %': symbol_stats['annualized_volatility'] * 100,
            'Best Day %': symbol_stats['best_day'] * 100,
            'Worst Day %': symbol_stats['worst_day'] * 100,
            'Win Rate %': symbol_stats['win_rate'] * 100,
            'Sharpe Ratio': symbol_stats['sharpe_ratio'],
            'Sortino Ratio': symbol_stats['sortino_ratio'],
        })
    
    if not stat_rows:
        st.info("Insufficient data for statistics calculation.")
        return
    
    stats_df = pd.DataFrame(stat_rows)
    
    # Display formatted table
    st.dataframe(
        stats_df.style.format({
            'Avg Daily Return %': '{:.3f}%',
            'Annual Volatility %': '{:.2f}%',
            'Best Day %': '{:.2f}%',
            'Worst Day %': '{:.2f}%',
            'Win Rate %': '{:.1f}%',
            'Sharpe Ratio': '{:.3f}',
            'Sortino Ratio': '{:.3f}',
        }),
        width="stretch",
        hide_index=True
    )
    
    st.caption(
        "**Sharpe Ratio:** Higher is better. Measures risk-adjusted returns. "
        "Simplified calculation assumes risk-free rate = 0."
    )
    render_accent_pills(
        [
            ("Symbols", str(len(stats_df))),
            ("Best Sharpe", f"{stats_df['Sharpe Ratio'].max():.3f}"),
            ("Best Sortino", f"{stats_df['Sortino Ratio'].max():.3f}"),
            ("Highest Vol", f"{stats_df['Annual Volatility %'].max():.2f}%"),
        ]
    )
