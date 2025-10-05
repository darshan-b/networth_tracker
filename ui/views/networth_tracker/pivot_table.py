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
    # Handle negative values for percent calculation
    if past_value != 0:
        percent_progress = (absolute_progress / abs(past_value)) * 100
    else:
        percent_progress = 0
    return absolute_progress, percent_progress


def color_pct(value):
    """Return HTML color-coded string for positive/negative percentages."""
    color = "green" if value >= 0 else "red"
    sign = "+" if value >= 0 else ""
    arrow = "↑" if value > 0 else "↓" if value < 0 else "→"
    return f"<span style='color:{color};'>{arrow} {sign}{value:.2f}%</span>"


def add_kpi_metrics(pivot_df, month_cols, comparison_type="month"):
    """
    Display key net worth metrics in Streamlit.
    
    Args:
        pivot_df (pd.DataFrame): Pivot table including Grand Total row.
        month_cols (list): List of month column names (already filtered by comparison type).
        comparison_type (str): "month", "Quarter", or "Year" for primary comparison.
    """
    st.markdown("### Key Metrics")
    grand_total_row = pivot_df.iloc[-1]

    last_value = grand_total_row[month_cols[-1]]
    first_value = grand_total_row[month_cols[0]]
    
    # Period-over-period change (last vs previous)
    prev_value = grand_total_row[month_cols[-2]] if len(month_cols) > 1 else last_value
    _, pct_change = calculate_progress(last_value, prev_value)

    # Total progress from first to last period
    total_progress, total_progress_pct = calculate_progress(last_value, first_value)

    # Four main KPI columns
    col1, col2, col3, col4 = st.columns(4)
    
    # Update label based on comparison type
    comparison_label = {"month": "MoM", "Quarter": "QoQ", "Year": "YoY"}[comparison_type]
    period_label = {"month": "month", "Quarter": "Quarter", "Year": "Year"}[comparison_type]
    
    with col1:
        st.metric("Current Net Worth", f"${last_value:,.0f}", f"{pct_change:,.2f}%" + f" ({comparison_label})")
    with col2:
        st.metric("Total Change", f"${total_progress:,.0f}", f"{total_progress_pct:,.2f}%")
    with col3:
        st.metric(f"{period_label}s Tracked", f"{len(month_cols)}")
    with col4:
        st.metric("Starting Net Worth", f"${first_value:,.0f}")


def create_pivot_table(filtered_df, rollup=True, comparison_type="month"):
    """
    Create a pivot table from filtered data, optionally rolled up by account_type,
    and add a Grand Total row. Filter columns based on comparison type.
    
    Args:
        filtered_df (pd.DataFrame): Filtered data containing 'account_type', 'category', 'month_Str', and 'amount'.
        rollup (bool): If True, summarize by account_type only. Otherwise, include category.
        comparison_type (str): "month", "Quarter", or "Year" to determine column intervals.
    
    Returns:
        tuple: (pivot_df, month_cols)
            pivot_df (pd.DataFrame): Pivot table including Grand Total.
            month_cols (list): Ordered list of month columns (filtered by comparison type).
    """
    months_order = filtered_df[['month', 'month_Str']].drop_duplicates().sort_values('month')
    all_month_cols = months_order['month_Str'].tolist()

    if rollup:
        pivot_df = pd.pivot_table(
            filtered_df,
            values='amount',
            index='account_type',
            columns='month_Str',
            aggfunc='sum',
            fill_value=0
        ).reset_index()
    else:
        pivot_df = pd.pivot_table(
            filtered_df,
            values='amount',
            index=['account_type', 'category'],
            columns='month_Str',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

    # Reorder columns to match chronological month order
    pivot_df = pivot_df[[*pivot_df.columns[:len(pivot_df.columns)-len(all_month_cols)], *all_month_cols]]

    # Filter columns based on comparison type (work backwards from most recent)
    interval_map = {"month": 1, "Quarter": 3, "Year": 12}
    interval = interval_map[comparison_type]
    
    # Select columns at the specified interval, starting from the most recent
    selected_indices = list(range(len(all_month_cols) - 1, -1, -interval))[::-1]  # Reverse to get chronological order
    
    # If we don't have enough data and first selected index > 0, include the first month
    if selected_indices and selected_indices[0] > 0 and len(selected_indices) == 1:
        selected_indices.insert(0, 0)  # Add first month if we only have one period
    elif selected_indices and selected_indices[0] > 0:
        # If first selected index isn't 0, prepend index 0 to include earliest data
        selected_indices.insert(0, 0)
    
    month_cols = [all_month_cols[i] for i in selected_indices]
    
    # Keep only selected month columns in the pivot table
    index_cols = [col for col in pivot_df.columns if col not in all_month_cols]
    pivot_df = pivot_df[index_cols + month_cols]

    # Add Grand Total row
    grand_total = pd.DataFrame([pivot_df[month_cols].sum().to_list()], columns=month_cols)
    grand_total.insert(0, 'account_type', 'Grand Total')
    pivot_df = pd.concat([pivot_df, grand_total], ignore_index=True)

    return pivot_df, month_cols


def style_grand_total_row(pivot_df, month_cols, comparison_type="month", pos_color="green", neg_color="red", max_lightness=80):
    """
    Apply HTML-based red/green gradient styling to the Grand Total row based on period-over-period changes.

    Args:
        pivot_df (pd.DataFrame): Pivot table including Grand Total row.
        month_cols (list): List of month column names in chronological order.
        comparison_type (str): "month", "Quarter", or "Year" for comparison period.
        pos_color (str): Color for positive changes.
        neg_color (str): Color for negative changes.
        max_lightness (int): Maximum lightness for color gradient.

    Returns:
        pd.DataFrame: Copy of pivot_df with styled Grand Total row.
    """
    styled_df = pivot_df.copy()
    last_row_idx = len(styled_df) - 1
    last_row_values = styled_df.loc[last_row_idx, month_cols].values.astype(float)

    # Since columns are already filtered by comparison type, always compare consecutive columns
    # Compute period-over-period percentage changes
    pct_changes = [0.0]  # First column has no previous
    for i in range(1, len(last_row_values)):
        _, pct = calculate_progress(last_row_values[i], last_row_values[i-1])
        pct_changes.append(pct)

    max_change = max(np.abs(pct_changes[1:]), default=1)
    max_intensity = 0.8
    styled_values = []
    for idx, val in enumerate(last_row_values):
        if idx == 0:
            # First column has no comparison
            styled_values.append(f"<div style='text-align:center; font-weight:bold'>{val:,.0f}</div>")
        else:
            pct = pct_changes[idx]
            sign = "+" if pct >= 0 else ""
            arrow = "↑" if pct > 0 else "↓" if pct < 0 else "→"
            # intensity: higher pct -> darker color
            intensity = min(abs(pct) / max_change, 1) ** 0.5
            # convert intensity to lightness: 0 -> 80%, 1 -> 40%
            lightness = max_lightness - (intensity * 60)
            hue = 120 if pct >= 0 else 0  # green or red
            styled_values.append(
                f"<div style='text-align:center; font-weight:bold'>"
                f"{val:,.0f} (<span style='color:hsl({hue}, 90%, {lightness}%);'>{arrow} {sign}{pct:.2f}%</span>)"
                f"</div>"
            )

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
    excel_df = pivot_df.copy()
    
    # Strip HTML tags
    for col in excel_df.columns:
        if excel_df[col].dtype == 'object':
            excel_df[col] = excel_df[col].astype(str).str.replace(r'<.*?>', '', regex=True)
    
    # Convert numeric columns
    for col in excel_df.columns:
        if col not in ['account_type', 'category']:
            try:
                excel_df[col] = pd.to_numeric(excel_df[col], errors='ignore')
            except:
                pass

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        excel_df.to_excel(writer, index=False, sheet_name="Pivot Table")
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


def validate_data(filtered_df):
    """
    Validate that the input data has required columns and structure.
    
    Args:
        filtered_df (pd.DataFrame): Input dataframe to validate.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    required_cols = ['account_type', 'category', 'month_Str', 'amount', 'month']
    
    missing_cols = [col for col in required_cols if col not in filtered_df.columns]
    if missing_cols:
        return False, f"Missing required columns: {', '.join(missing_cols)}"
    
    if filtered_df.empty:
        return False, "No data available for the selected filters."
    
    if filtered_df['amount'].isna().all():
        return False, "All amount values are missing."
    
    return True, ""


def show_pivot_table(filtered_df):
    """
    Main function to display pivot table with KPIs, styling, Excel export, and optional transpose.
    
    Args:
        filtered_df (pd.DataFrame): Filtered dataset with 'account_type', 'category', 'month_Str', and 'amount'.
    """
    st.header("Summarized Table")
    
    # Validate data
    is_valid, error_msg = validate_data(filtered_df)
    if not is_valid:
        st.error(f"Data Error: {error_msg}")
        st.info("Please ensure your data contains: account_type, category, month_Str, amount, and month columns.")
        st.stop()
    
    # Check if we have enough data
    unique_months = filtered_df['month_Str'].nunique()
    if unique_months < 2:
        st.warning("Need at least 2 periods of data for meaningful comparisons.")
        st.info(f"Currently have data for {unique_months} period(s). Please add more data or adjust filters.")
        st.stop()

    # Controls
    col1, col2, col3 = st.columns(3)
    with col1:
        rollup_val = st.checkbox("Roll up categories?", value=True)
    with col2:
        transpose_val = st.checkbox("Transpose pivot table?", value=False)
    with col3:
        comparison_type = st.selectbox("Comparison Period:", ["month", "Quarter", "Year"], index=0)

    # Create pivot table and compute KPIs
    pivot_df, month_cols = create_pivot_table(filtered_df, rollup_val, comparison_type)
    
    # Check if we have enough periods for the selected comparison type
    if len(month_cols) < 2:
        st.warning(f"Not enough data points for {comparison_type} comparison.")
        st.info(f"Need at least 2 {comparison_type.lower()}s of data. Currently have {len(month_cols)} period(s).")
        st.stop()
    
    add_kpi_metrics(pivot_df, month_cols, comparison_type)

    # Apply Grand Total row styling with selected comparison type
    styled_df = style_grand_total_row(pivot_df, month_cols, comparison_type)

    # Optional transpose
    if transpose_val:
        styled_df = styled_df.rename(columns={'account_type':'month'}).set_index('month').T
    else:
        styled_df.set_index('account_type', inplace=True)
        
    # Excel export (clean numbers)
    export_to_excel(pivot_df)

    # Render HTML table with styling
    render_html_table(styled_df)