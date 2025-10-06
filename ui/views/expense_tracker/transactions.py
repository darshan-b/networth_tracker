"""Transactions tab for expense tracker.

Provides transaction filtering, search, and detailed view of all transactions.
"""

import streamlit as st
import pandas as pd
from constants import ColumnNames
from pivottablejs import pivot_ui
import streamlit.components.v1 as components
import json


def render_transactions_tab(df):
    """
    Render the transactions management tab with filtering and search capabilities.
    
    Args:
        df (pd.DataFrame): Transactions dataframe (includes both expenses and income)
    
    Returns: None
    """
    st.subheader("Transactions")
    
    if df.empty:
        st.info("No transactions available for the selected period.")
        return
    
    # Display summary metrics
    _render_transaction_summary(df)

    # Render filters with cascading logic
    df_filtered = _apply_transaction_filters(df)
    
    if df_filtered.empty:
        st.warning("No transactions match the selected filters.")
        return

    # Display transaction table
    _render_transaction_table(df_filtered)
    # Display transaction count
    st.caption(f"Showing {len(df_filtered):,} of {len(df):,} transactions")
    
    st.markdown("### Experimental Pivot Table")
    _render_pivot_table(df_filtered)


def _apply_transaction_filters(df):
    """
    Render filter controls with cascading logic and apply filtering.
    
    Args:
        df (pd.DataFrame): Original transactions dataframe
        
    Returns:
        pd.DataFrame: Filtered transactions dataframe
    """
    st.markdown("### Filters")

    if 'filter_reset_counter' not in st.session_state:
        st.session_state.filter_reset_counter = 0
    
    # First row: Account and Search
    col1, col2 = st.columns([2, 2])
    
    with col1:
        available_accounts = sorted(df[ColumnNames.ACCOUNT].unique())
        account_filter = st.multiselect(
            "Account", 
            options=available_accounts,
            default=available_accounts,
            help="Filter by account(s)",
            key=f"account_filter_{st.session_state.filter_reset_counter}"
        )
    
    with col2:
        search_merchant = st.text_input(
            "Search Merchant", 
            "",
            placeholder="Type to search...",
            help="Search by merchant name",
            key=f"search_merchant_{st.session_state.filter_reset_counter}"
        )
    
    # Filter by account first for cascading
    df_temp = df[df[ColumnNames.ACCOUNT].isin(account_filter)] if account_filter else df
    
    # Second row: Category and Subcategory (cascading)
    col3, col4 = st.columns([2, 2])
    
    with col3:
        # Only show categories that exist in the filtered accounts
        available_categories = sorted(df_temp[ColumnNames.CATEGORY].unique())
        category_filter = st.multiselect(
            "Category",
            options=available_categories,
            default=available_categories,
            help="Filter by category - updates based on account selection",
            key=f"category_filter_{st.session_state.filter_reset_counter}"
        )
    
    # Filter by category for subcategory options
    df_temp = df_temp[df_temp[ColumnNames.CATEGORY].isin(category_filter)] if category_filter else df_temp
    
    with col4:
        # Only show subcategories that exist in the filtered categories
        available_subcategories = sorted(df_temp[ColumnNames.SUBCATEGORY].unique())
        subcategory_filter = st.multiselect(
            "Subcategory",
            options=available_subcategories,
            default=available_subcategories,
            help="Filter by subcategory - updates based on category selection",
            key=f"subcategory_filter_{st.session_state.filter_reset_counter}"
        )
    
    # Apply all filters
    df_filtered = df[
        (df[ColumnNames.ACCOUNT].isin(account_filter)) &
        (df[ColumnNames.CATEGORY].isin(category_filter)) &
        (df[ColumnNames.SUBCATEGORY].isin(subcategory_filter))
    ]
    
    # Apply merchant search
    if search_merchant:
        df_filtered = df_filtered[
            df_filtered[ColumnNames.MERCHANT].str.contains(
                search_merchant, 
                case=False, 
                na=False
            )
        ]
    
    # Clear filters button
    if st.button("Reset All Filters", use_container_width=False):
        st.session_state.filter_reset_counter += 1
        st.rerun()
    
    st.divider()
    
    return df_filtered


def _render_transaction_table(df_filtered):
    """
    Render the transactions table with proper formatting.
    
    Args:
        df_filtered (pd.DataFrame): Filtered transactions dataframe
    """
    df_display = df_filtered.sort_values(ColumnNames.DATE, ascending=False).copy()
    
    # Create display amount column
    df_display['display_amount'] = df_display.apply(
        lambda row: abs(row[ColumnNames.AMOUNT]) if row[ColumnNames.CATEGORY] != 'Income' else row[ColumnNames.AMOUNT], 
        axis=1
    )
    
    # Add transaction type indicator
    df_display['type'] = df_display[ColumnNames.CATEGORY].apply(
        lambda x: 'Income' if x == 'Income' else 'Expense'
    )
    
    st.dataframe(
        df_display[[ColumnNames.DATE, 'type', ColumnNames.MERCHANT, ColumnNames.CATEGORY, ColumnNames.SUBCATEGORY, ColumnNames.ACCOUNT, 'display_amount']],
        use_container_width=True,
        hide_index=True,
        column_config={
            ColumnNames.DATE: st.column_config.DateColumn(
                "Date",
                format="MMM DD, YYYY"
            ),
            "type": st.column_config.TextColumn(
                "Type",
                width="small"
            ),
            "merchant": st.column_config.TextColumn(
                "Merchant",
                width="medium"
            ),
            ColumnNames.CATEGORY: st.column_config.TextColumn(
                "Category",
                width="medium"
            ),
            ColumnNames.SUBCATEGORY: st.column_config.TextColumn(
                "Subcategory",
                width="medium"
            ),
            "account": st.column_config.TextColumn(
                "Account",
                width="medium"
            ),
            "display_amount": st.column_config.NumberColumn(
                "Amount", 
                format="$%.2f",
                width="small"
            ),
        }
    )


def _render_transaction_summary(df_filtered):
    """
    Display summary metrics for filtered transactions.
    
    Args:
        df_filtered (pd.DataFrame): Filtered transactions dataframe
    """
    col1, col2, col3 = st.columns(3)
    
    # Calculate metrics
    expenses_filtered = df_filtered[df_filtered[ColumnNames.CATEGORY] != 'Income']
    expenses_total = abs(expenses_filtered[ColumnNames.AMOUNT].sum())
    expenses_count = len(expenses_filtered)
    
    income_filtered = df_filtered[df_filtered[ColumnNames.CATEGORY] == 'Income']
    income_total = income_filtered[ColumnNames.AMOUNT].sum()
    income_count = len(income_filtered)
    
    net_total = income_total - expenses_total
    
    with col1:
        st.metric(
            "Total Expenses", 
            f"${expenses_total:,.2f}",
            delta=f"{expenses_count} transactions",
            delta_color="off"
        )
    
    with col2:
        st.metric(
            "Total Income", 
            f"${income_total:,.2f}",
            delta=f"{income_count} transactions",
            delta_color="off"
        )
    
    with col3:
        st.metric( 
            "Savings (Income - Expenses)", 
            f"${net_total:,.2f}",
            delta="+Under" if net_total >= 0 else "-Over",
            delta_color="normal"
        )


def _render_pivot_table(df_display):
    # Add transaction type indicator
    df_display['type'] = df_display[ColumnNames.CATEGORY].apply(
        lambda x: 'Income' if x == 'Income' else 'Expense'
    )
    
    df_for_pivot = df_display[[ColumnNames.DATE, 'type', ColumnNames.MERCHANT, ColumnNames.CATEGORY, ColumnNames.SUBCATEGORY, ColumnNames.ACCOUNT, ColumnNames.AMOUNT]].copy()

    # Convert date to string to avoid UTC conversion
    df_for_pivot[ColumnNames.DATE] = df_for_pivot[ColumnNames.DATE].dt.strftime('%Y-%m-%d')
    # Convert to JSON
    data_json = df_for_pivot.to_json(orient='records')

    default_rows = [ColumnNames.DATE, ColumnNames.CATEGORY, ColumnNames.SUBCATEGORY]
    default_vals = [ColumnNames.AMOUNT]

    # Convert to JSON strings for JavaScript
    rows_json = json.dumps(default_rows)
    vals_json = json.dumps(default_vals)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pivottable@2.23.0/dist/pivot.min.css">
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/pivottable@2.23.0/dist/pivot.min.js"></script>
        <script src="https://cdn.plot.ly/plotly-basic-latest.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/pivottable@2.23.0/dist/plotly_renderers.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 5px;
            }}
            #output {{
                width: 98vw;  /* 98% of viewport width */
                max-width: none;
                font-size:16px;
            }}
            .pvtTable {{
                font-size: 16pt;
                width: 100% !important;
            }}
            .pvtVals{{
                font-size:16px;
            }}
            table.pvtTable {{
                font-size: 14px !important;
            }}
            table.pvtTable tbody tr th,
            table.pvtTable thead tr th {{
                font-size: 14px !important;  /* Changed from 8pt */
                padding: 8px;  /* Increased padding */
            }}
        </style>
    </head>
    <body>
        <div id="output"></div>
        <script>
            // Exact pattern from documentation
            $(function(){{
                var derivers = $.pivotUtilities.derivers;
                var renderers = $.extend($.pivotUtilities.renderers,
                    $.pivotUtilities.plotly_renderers);

                var mps = {data_json};  // Instead of $.getJSON("mps.json")
                
                $("#output").pivotUI(mps, {{
                    renderers: renderers,
                    rows: {rows_json},
                    rendererName: "Table",
                    vals: {vals_json},
                    aggregatorName: "Sum"
                }});
            }});
        </script>
    </body>
    </html>
    """

    # Display
    components.html(html_code, height=500, scrolling=True)
