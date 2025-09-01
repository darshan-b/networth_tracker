import streamlit as st
import pandas as pd
import numpy as np
import io


def calculate_progress(current_value, past_value):
    """
    Calculate absolute and percent progress between two values safely.
    
    Args:
        current_value (float): Current value.
        past_value (float): Previous value to compare with.
    
    Returns:
        tuple: (absolute_progress, percent_progress)
    """
    absolute_progress = current_value - past_value
    percent_progress = (absolute_progress / past_value * 100) if past_value > 0 else 0
    return absolute_progress, percent_progress


def color_pct(value):
    """Return HTML color-coded string for positive/negative percentages."""
    color = "green" if value >= 0 else "red"
    sign = "+" if value >= 0 else ""
    return f"<span style='color:{color};'>{sign}{value:.2f}%</span>"


def render_kpi(col, title, value, pct_text="", separator=False):
    """
    Render a KPI in a Streamlit column with optional vertical separator.

    Args:
        col: Streamlit column object (from st.columns).
        title: KPI title (str).
        value: Main value (str or number).
        pct_text: Percent text, optionally color-coded (str).
        separator: Whether to show vertical line on the right (bool).
    """
    separator_style = "border-right:2px solid #ddd; padding-right:10px;" if separator else ""
    col.markdown(f"""
        <div style="{separator_style}">
            <div style='font-size:14px; color:#555; font-weight:bold;'>{title}</div>
            <div style='font-size:24px; font-weight:bold; margin-top:3px;'>{value}</div>
            <div style='font-size:14px; margin-top:3px;'>{pct_text}</div>
        </div>
    """, unsafe_allow_html=True)


def add_kpi_metrics(pivot_df, month_cols):
    """
    Display key net worth metrics in Streamlit.
    
    Args:
        pivot_df (pd.DataFrame): Pivot table including Grand Total row.
        month_cols (list): List of month column names in chronological order.
    """
    st.markdown("### Key Metrics")
    grand_total_row = pivot_df.iloc[-1]

    last_month_value = grand_total_row[month_cols[-1]]
    prev_month_value = grand_total_row[month_cols[-2]] if len(month_cols) > 1 else last_month_value
    pct_change = ((last_month_value - prev_month_value) / max(prev_month_value, 1)) * 100

    three_months_ago_value = grand_total_row[month_cols[-4]] if len(month_cols) > 3 else 0
    progress_absolute, progress_pct = calculate_progress(last_month_value, three_months_ago_value)

    # Predefined comparison range
    range_options = ["1 Month", "3 Months", "6 Months", "12 Months"]
    range_choice = st.radio("Select comparison range:", range_options, horizontal=True)
    n_months = {"1 Month": 1, "3 Months": 3, "6 Months": 6, "12 Months": 12}[range_choice]

    # Ensure we don’t go before available months
    n_months = min(n_months, len(month_cols)-1)
    value_n_months_ago = grand_total_row[month_cols[-(n_months+1)]] if len(month_cols) > n_months else 0
    progress_n_months, progress_n_months_pct = calculate_progress(last_month_value, value_n_months_ago)

    # Four main KPI columns
    col1, col2, col3, col4 = st.columns(4)
    
    render_kpi(col1, "Total Net Worth", f"${last_month_value:,.0f}", color_pct(pct_change), separator=True)
    render_kpi(col2, "90-Day Progress", f"${progress_absolute:,.0f}", color_pct(progress_pct), separator=True)
    render_kpi(col3, "Months Tracked", f"{len(month_cols)}", "", separator=True)
    render_kpi(col4, f"{n_months}-Month Progress", f"${progress_n_months:,.0f}", color_pct(progress_n_months_pct), separator=False)


def create_pivot_table(filtered_df, rollup=True):
    """
    Create a pivot table from filtered dat, optionally rolled up by Account Type,
    and add a Grand Total row.
    
    Args:
        filtered_df (pd.DataFrame): Filtered data containing 'Account Type', 'Category', 'Month_Str', and 'Amount'.
        rollup (bool): If True, summarize by Account Type only. Otherwise, include Category.
    
    Returns:
        tuple: (pivot_df, month_cols)
            pivot_df (pd.DataFrame): Pivot table including Grand Total.
            month_cols (list): Ordered list of month columns.
    """
    months_order = filtered_df[['Month', 'Month_Str']].drop_duplicates().sort_values('Month')
    month_cols = months_order['Month_Str'].tolist()

    if rollup:
        pivot_df = pd.pivot_table(
            filtered_df,
            values='Amount',
            index='Account Type',
            columns='Month_Str',
            aggfunc='sum',
            fill_value=0
        ).reset_index()
    else:
        pivot_df = pd.pivot_table(
            filtered_df,
            values='Amount',
            index=['Account Type', 'Category'],
            columns='Month_Str',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

    # Reorder columns to match chronological month order
    pivot_df = pivot_df[[*pivot_df.columns[:len(pivot_df.columns)-len(month_cols)], *month_cols]]

    # Add Grand Total row
    grand_total = pd.DataFrame([pivot_df[month_cols].sum().to_list()], columns=month_cols)
    grand_total.insert(0, 'Account Type', 'Grand Total')
    pivot_df = pd.concat([pivot_df, grand_total], ignore_index=True)

    return pivot_df, month_cols


def style_grand_total_row(pivot_df, month_cols, pos_color="green", neg_color="red", max_lightness=80):
    """
    Apply HTML-based red/green gradient styling to the Grand Total row based on month-over-month changes.

    Args:
        pivot_df (pd.DataFrame): Pivot table including Grand Total row.
        month_cols (list): List of month column names in chronological order.
        pos_color (str): Color for positive changes.
        neg_color (str): Color for negative changes.
        max_lightness (int): Maximum lightness for color gradient.

    Returns:
        pd.DataFrame: Copy of pivot_df with styled Grand Total row.
    """
    styled_df = pivot_df.copy()
    last_row_idx = len(styled_df) - 1
    last_row_values = styled_df.loc[last_row_idx, month_cols].values.astype(float)

    # Compute month-over-month percentage changes using calculate_progress
    pct_changes = [0.0]  # First month has no previous
    for i in range(1, len(last_row_values)):
        _, pct = calculate_progress(last_row_values[i], last_row_values[i-1])
        pct_changes.append(pct)

    max_change = max(np.abs(pct_changes[1:]), default=1)
    max_intensity = 0.8
    styled_values = []
    for idx, val in enumerate(last_row_values):
        if idx == 0:
            # just show the value for first column
            styled_values.append(f"<div style='text-align:center; font-weight:bold'>{val:,.0f}</div>")
        else:
            pct = pct_changes[idx]
            sign = "+" if pct >= 0 else ""
            # intensity: higher pct -> darker color
            intensity = min(abs(pct) / max_change, 1) ** 0.5
            # convert intensity to lightness: 0 -> 80%, 1 -> 40%
            lightness = max_lightness - (intensity * 60)
            hue = 120 if pct >= 0 else 0  # green or red
            styled_values.append(
                f"<div style='text-align:center; font-weight:bold'>"
                f"{val:,.0f} (<span style='color:hsl({hue}, 90%, {lightness}%);'>{sign}{pct:.2f}%</span>)"
                f"</div>"
            )
    # for idx, val in enumerate(last_row_values):
    #     if idx == 0:
    #         # First column: just show value
    #         styled_values.append(f"<div style='text-align:center; font-weight:bold'>{val:,.0f}</div>")
    #     else:
    #         pct = pct_changes[idx]
    #         sign = "+" if pct >= 0 else ""
    #         intensity = min(abs(pct) / max_change, 1) ** 0.5
    #         lightness = max_lightness - (intensity * 60)
    #         text_color = "black" if pct >= 0 else "white"

    #         styled_html = (
    #             f"<div style='background-color:hsl({0 if pct<0 else 120},90%,{lightness}%);"
    #             f"color:{text_color}; font-weight:bold; text-align:center; padding:4px; border:1px solid #ccc;'>"
    #             f"{val:,.0f} ({sign}{pct:.2f}%)</div>"
    #         )
    #         styled_values.append(styled_html)

    # Assign all styled values at once
    for col, html in zip(month_cols, styled_values):
        styled_df.at[last_row_idx, col] = html

    return styled_df


def export_to_excel(pivot_df):
    """
    Export pivot table to Excel, stripping HTML for clean numeric values.
    
    Args:
        pivot_df (pd.DataFrame): Pivot table (may include HTML in cells).
    """
    excel_df = pivot_df.replace(r'<.*?>', '', regex=True)
    numeric_cols = excel_df.select_dtypes('number').columns.tolist()
    excel_df[numeric_cols] = excel_df[numeric_cols].astype(float)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        excel_df.to_excel(writer, index=True, sheet_name="Pivot Table")
    buffer.seek(0)
    st.download_button(
        "Download Pivot Table (Excel)",
        data=buffer,
        file_name="pivot_table.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def render_html_table(styled_df):
    """
    Render pivot table as an HTML table with centered cells in Streamlit.
    
    Args:
        styled_df (pd.DataFrame): Pivot table with HTML styling applied.
    """
    html_table = styled_df.to_html(escape=False, index=True)
    html_table = html_table.replace(
        '<table border="1" class="dataframe">',
        '<table border="1" style="width:100%; text-align:center; border-collapse:collapse;">'
    )
    html_table = html_table.replace('<th>', '<th style="text-align:center; vertical-align:middle;">')
    html_table = html_table.replace('<td>', '<td style="text-align:center; vertical-align:middle;">')
    st.write(html_table, unsafe_allow_html=True)


def show_pivot_table(filtered_df):
    """
    Main function to display pivot table with KPIs, styling, Excel export, and optional transpose.
    
    Args:
        filtered_df (pd.DataFrame): Filtered dataset with 'Account Type', 'Category', 'Month_Str', and 'Amount'.
    """
    st.header("Summarized Table")

    col1, col2 = st.columns(2)
    with col1:
        rollup_val = st.checkbox("Roll up categories?", value=True)
    with col2:
        transpose_val = st.checkbox("Transpose pivot table?", value=False)

    # Create pivot table and compute KPIs
    pivot_df, month_cols = create_pivot_table(filtered_df, rollup_val)
    add_kpi_metrics(pivot_df, month_cols)

    # Apply Grand Total row styling (your original logic)
    styled_df = style_grand_total_row(pivot_df, month_cols)

    # Optional transpose
    if transpose_val:
        styled_df = styled_df.rename(columns={'Account Type':'Month'}).set_index('Month').T

    else:
        styled_df.set_index('Account Type', inplace=True)
    # Excel export (clean numbers)
    export_to_excel(pivot_df)

    # Render HTML table with styling
    render_html_table(styled_df)
