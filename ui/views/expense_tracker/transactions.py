"""Transactions tab for expense tracker.

Provides transaction filtering, search, and detailed view of all transactions.
"""

import streamlit as st
import pandas as pd
import json
from urllib.parse import quote

from app_constants import ColumnNames
from data.calculations import (
    classify_transaction_type,
    is_expense_transaction,
    is_income_transaction,
    is_refund_transaction,
)
from ui.components.surfaces import (
    inject_surface_styles,
    render_metric_card,
    render_page_hero,
    render_section_intro,
)


def render_transactions_tab(df):
    """
    Render the transactions management tab with filtering and search capabilities.
    
    Args:
        df (pd.DataFrame): Transactions dataframe (includes both expenses and income)
    
    Returns: None
    """
    inject_surface_styles()
    render_page_hero(
        "Expenses",
        "Transactions",
        "Search, filter, and review raw transaction activity across the selected period.",
        "Use this tab when you need exact rows, not just summaries.",
    )
    
    if df.empty:
        st.info("No transactions available for the selected period.")
        return
    
    render_section_intro(
        "Filters",
        "Refine the transaction list by account, category, subcategory, and merchant.",
    )
    df_filtered = _apply_transaction_filters(df)
    
    if df_filtered.empty:
        st.warning("No transactions match the selected filters.")
        return

    render_section_intro(
        "Snapshot",
        "A quick read on the filtered expense, income, and net savings mix.",
    )
    _render_transaction_summary(df_filtered)

    render_section_intro(
        "Transaction List",
        "Review the filtered rows directly or export them for follow-up work.",
    )
    action_col1, action_col2 = st.columns([1, 4])
    with action_col1:
        export_df = _build_export_dataframe(df_filtered)
        st.download_button(
            "Download CSV",
            data=export_df.to_csv(index=False),
            file_name="filtered_transactions.csv",
            mime="text/csv",
            width="content",
        )

    # Display transaction table
    _render_transaction_table(df_filtered)
    # Display transaction count
    st.caption(f"Showing {len(df_filtered):,} of {len(df):,} transactions")
    
    render_section_intro(
        "Pivot Explorer",
        "Use the experimental pivot below for ad hoc slicing after you narrow the transaction set.",
    )
    _render_pivot_table(df_filtered)


def _apply_transaction_filters(df):
    """
    Render filter controls with cascading logic and apply filtering.
    
    Args:
        df (pd.DataFrame): Original transactions dataframe
        
    Returns:
        pd.DataFrame: Filtered transactions dataframe
    """
    if 'filter_reset_counter' not in st.session_state:
        st.session_state.filter_reset_counter = 0
    
    # First row: Type, Account, Search
    col1, col2, col3 = st.columns([1.2, 2, 2])

    with col1:
        type_filter = st.multiselect(
            "Type",
            options=["Expense", "Refund/Credit", "Income"],
            default=["Expense", "Refund/Credit", "Income"],
            help="Filter by transaction type",
            key=f"type_filter_{st.session_state.filter_reset_counter}",
        )

    with col2:
        available_accounts = sorted(df[ColumnNames.ACCOUNT].unique())
        account_filter = st.multiselect(
            "Account", 
            options=available_accounts,
            default=available_accounts,
            help="Filter by account(s)",
            key=f"account_filter_{st.session_state.filter_reset_counter}"
        )
    
    with col3:
        search_merchant = st.text_input(
            "Search Merchant", 
            "",
            placeholder="Type to search...",
            help="Search by merchant name",
            key=f"search_merchant_{st.session_state.filter_reset_counter}"
        )
    
    # Filter by type/account first for cascading
    df_temp = df.copy()
    if type_filter and len(type_filter) < 3:
        mask = pd.Series(False, index=df_temp.index)
        if "Expense" in type_filter:
            mask = mask | is_expense_transaction(df_temp)
        if "Refund/Credit" in type_filter:
            mask = mask | is_refund_transaction(df_temp)
        if "Income" in type_filter:
            mask = mask | is_income_transaction(df_temp)
        df_temp = df_temp[mask]

    df_temp = df_temp[df_temp[ColumnNames.ACCOUNT].isin(account_filter)] if account_filter else df_temp

    # Second row: Category and Subcategory (cascading)
    col4, col5 = st.columns([2, 2])
    
    with col4:
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
    
    with col5:
        # Only show subcategories that exist in the filtered categories
        available_subcategories = sorted(df_temp[ColumnNames.SUBCATEGORY].unique())
        subcategory_filter = st.multiselect(
            "Subcategory",
            options=available_subcategories,
            default=available_subcategories,
            help="Filter by subcategory - updates based on category selection",
            key=f"subcategory_filter_{st.session_state.filter_reset_counter}"
        )
    
    # Third row: amount range
    amount_series = df_temp[ColumnNames.AMOUNT].abs()
    amount_min = float(amount_series.min()) if not amount_series.empty else 0.0
    amount_max = float(amount_series.max()) if not amount_series.empty else 0.0

    amount_range = st.slider(
        "Amount Range",
        min_value=float(amount_min),
        max_value=float(amount_max if amount_max > amount_min else amount_min + 1),
        value=(float(amount_min), float(amount_max if amount_max > amount_min else amount_min + 1)),
        step=max((amount_max - amount_min) / 100, 1.0),
        help="Filter by absolute transaction amount",
        key=f"amount_range_{st.session_state.filter_reset_counter}",
    )

    # Apply all filters
    df_filtered = df.copy()

    if type_filter and len(type_filter) < 3:
        mask = pd.Series(False, index=df_filtered.index)
        if "Expense" in type_filter:
            mask = mask | is_expense_transaction(df_filtered)
        if "Refund/Credit" in type_filter:
            mask = mask | is_refund_transaction(df_filtered)
        if "Income" in type_filter:
            mask = mask | is_income_transaction(df_filtered)
        df_filtered = df_filtered[mask]

    df_filtered = df_filtered[
        (df_filtered[ColumnNames.ACCOUNT].isin(account_filter)) &
        (df_filtered[ColumnNames.CATEGORY].isin(category_filter)) &
        (df_filtered[ColumnNames.SUBCATEGORY].isin(subcategory_filter))
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

    df_filtered = df_filtered[
        df_filtered[ColumnNames.AMOUNT].abs().between(amount_range[0], amount_range[1])
    ]
    
    # Clear filters button
    if st.button("Reset All Filters", width="content"):
        st.session_state.filter_reset_counter += 1
        st.rerun()
    
    st.divider()
    
    return df_filtered


def _build_export_dataframe(df_filtered: pd.DataFrame) -> pd.DataFrame:
    """Prepare a clean export of the currently filtered transaction set."""
    export_df = df_filtered.sort_values(ColumnNames.DATE, ascending=False).copy()
    export_df["Type"] = export_df.apply(classify_transaction_type, axis=1)
    export_df["Display Amount"] = export_df.apply(
        lambda row: abs(row[ColumnNames.AMOUNT]) if classify_transaction_type(row) != "Income" else row[ColumnNames.AMOUNT],
        axis=1,
    )
    return export_df


def _render_transaction_table(df_filtered):
    """
    Render the transactions table with proper formatting.
    
    Args:
        df_filtered (pd.DataFrame): Filtered transactions dataframe
    """
    df_display = df_filtered.sort_values(ColumnNames.DATE, ascending=False).copy()
    
    # Create display amount column
    df_display['display_amount'] = df_display.apply(
        lambda row: abs(row[ColumnNames.AMOUNT]) if classify_transaction_type(row) != 'Income' else row[ColumnNames.AMOUNT], 
        axis=1
    )
    
    # Add transaction type indicator
    df_display['type'] = df_display.apply(classify_transaction_type, axis=1)
    
    st.dataframe(
        df_display[[ColumnNames.DATE, 'type', ColumnNames.MERCHANT, ColumnNames.CATEGORY, ColumnNames.SUBCATEGORY, ColumnNames.ACCOUNT, 'display_amount']],
        width="stretch",
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
    expenses_filtered = df_filtered[is_expense_transaction(df_filtered)]
    refunds_filtered = df_filtered[is_refund_transaction(df_filtered)]
    expenses_total = abs(expenses_filtered[ColumnNames.AMOUNT].sum()) - refunds_filtered[ColumnNames.AMOUNT].sum()
    expenses_total = max(expenses_total, 0.0)
    expenses_count = len(expenses_filtered)
    
    income_filtered = df_filtered[is_income_transaction(df_filtered)]
    income_total = income_filtered[ColumnNames.AMOUNT].sum()
    income_count = len(income_filtered)
    refund_total = refunds_filtered[ColumnNames.AMOUNT].sum()
    refund_count = len(refunds_filtered)
    
    net_total = df_filtered[ColumnNames.AMOUNT].sum()
    
    with col1:
        render_metric_card(
            "Net Expenses",
            f"${expenses_total:,.0f}",
            f"{expenses_count} transactions",
            "Expense outflows after refunds and credits reduce the total.",
            "negative",
        )
    
    with col2:
        render_metric_card(
            "Refunds / Credits",
            f"${refund_total:,.0f}",
            f"{refund_count} transactions",
            "Positive non-income transactions that offset spending.",
            "positive" if refund_total > 0 else "neutral",
        )
    
    with col3:
        render_metric_card(
            "Net Cash Flow",
            f"${net_total:,.0f}",
            f"${income_total:,.0f} income",
            "All signed transactions summed across the filtered set.",
            "positive" if net_total > 0 else "negative" if net_total < 0 else "neutral",
        )


def _render_pivot_table(df_display):
    # Add transaction type indicator
    df_display['type'] = df_display.apply(classify_transaction_type, axis=1)
    
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
    st.iframe(f"data:text/html;charset=utf-8,{quote(html_code)}", height=500)
