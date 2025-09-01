\# Financial Dashboard



This Streamlit application provides a comprehensive view of your financial accounts, with multiple visualization modes and key metrics. It is designed to help you track month-over-month progress, view summaries by account type and category, and quickly assess your financial position.



---



\## Tabs Overview



\### Tab 1: Chart View

\- Displays interactive \*\*bar and line charts\*\* of selected accounts and categories.

\- Allows filtering by:

&nbsp; - \*\*Account Type\*\* (multi-select)

&nbsp; - \*\*Category\*\* (multi-select)

&nbsp; - \*\*Account\*\* (multi-select)

\- Features:

&nbsp; - \*\*Monthly total line chart\*\* showing month-over-month progress.

&nbsp; - Color-coded bars for account balances.

&nbsp; - Hover information shows exact values.

\- \*\*Use case:\*\* Quickly visualize trends and account balances over time.



---



\### Tab 2: Pivot Table View

\- Displays a \*\*pivot table\*\* summarizing account balances by month.

\- Features:

&nbsp; - Option to \*\*roll up categories\*\* or view detailed account/category breakdown.

&nbsp; - Optional \*\*transpose view\*\* for easier horizontal reading.

&nbsp; - \*\*Grand Total row\*\* with month-over-month change percentages.

&nbsp; - \*\*Color-coded cells\*\* for positive (green) and negative (red) changes.

&nbsp; - Export functionality:

&nbsp;   - Download the pivot table as \*\*Excel\*\*, with original numeric values (no HTML formatting).

\- \*\*Use case:\*\* Detailed tabular view to analyze month-by-month account balances.



---



\### Tab 3: Month-over-Month Progress

\- Displays \*\*line chart(s)\*\* showing financial progress over months.

\- Features:

&nbsp; - Shows \*\*monthly totals\*\* or account/category-specific lines.

&nbsp; - Optional \*\*rolling month-over-month % change\*\*.

&nbsp; - Markers and labels display values in \*\*k units\*\* for readability.

&nbsp; - Customizable text size and positioning.

\- \*\*Use case:\*\* Track the growth or decline of total balances or specific accounts over time.



---



\### Tab 4: Dashboard Overview

\- Combines multiple visualizations in a \*\*2x2 grid\*\* for a high-level summary.

\- Subplots include:

&nbsp; 1. \*\*Monthly Total Line Chart\*\*

&nbsp; 2. \*\*Account Type Distribution (Bar Chart)\*\*

&nbsp; 3. \*\*Category Distribution (Pie Chart)\*\*

&nbsp; 4. \*\*Treemap\*\* showing account and category balances for the latest month

&nbsp;    - Automatically adjusts \*\*Liabilities\*\* as negative values.

&nbsp;    - Displays hover info with labels, values, and percentages.

\- Additional features:

&nbsp; - Interactive \*\*filters\*\* are consistent across all tabs.

&nbsp; - Hover and text formatting are preserved for clarity.

\- \*\*Use case:\*\* Get an at-a-glance overview of your financial position, distributions, and detailed breakdowns in one view.



---



\## Key Features

\- Fully interactive charts using \*\*Plotly\*\*.

\- \*\*Dynamic filtering\*\* by account type, category, and individual account.

\- Download pivot tables in \*\*Excel\*\* format.

\- Color-coded insights for quick assessment:

&nbsp; - Green = positive growth

&nbsp; - Red = negative growth

\- Modular design with \*\*4 tabs\*\* for different analysis perspectives.



---



\## Future Enhancements

\- Add \*\*KPI cards\*\* with Net Worth, Cash %, Liabilities %, and MoM changes.

\- Add \*\*trend charts\*\* for cumulative net worth over time.

\- Enable \*\*PDF / JPEG exports\*\* of dashboards.

\- Include \*\*benchmarking / target comparisons\*\*.

\- Mobile-friendly responsive layout.



