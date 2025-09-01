# Financial Dashboard

This Streamlit application provides a comprehensive view of your financial accounts, with multiple visualization modes and key metrics. It is designed to help you track month-over-month progress, view summaries by account type and category, and quickly assess your financial position.

---

## Tabs Overview

### Tab 1: Chart View
- Displays interactive **bar and line charts** of selected accounts and categories.
- Allows filtering by:
  - **Account Type** (multi-select)
  - **Category** (multi-select)
  - **Account** (multi-select)
- Features:
  - **Monthly total line chart** showing month-over-month progress.
  - Color-coded bars for account balances.
  - Hover information shows exact values.
- **Use case:** Quickly visualize trends and account balances over time.

---

### Tab 2: Pivot Table View
- Displays a **pivot table** summarizing account balances by month.
- Features:
  - Option to **roll up categories** or view detailed account/category breakdown.
  - Optional **transpose view** for easier horizontal reading.
  - **Grand Total row** with month-over-month change percentages.
  - **Color-coded cells** for positive (green) and negative (red) changes.
  - Export functionality:
    - Download the pivot table as **Excel**, with original numeric values (no HTML formatting).
- **Use case:** Detailed tabular view to analyze month-by-month account balances.

---

### Tab 3: Month-over-Month Progress
- Displays **line chart(s)** showing financial progress over months.
- Features:
  - Shows **monthly totals** or account/category-specific lines.
  - Optional **rolling month-over-month % change**.
  - Markers and labels display values in **k units** for readability.
  - Customizable text size and positioning.
- **Use case:** Track the growth or decline of total balances or specific accounts over time.

---

### Tab 4: Dashboard Overview
- Combines multiple visualizations in a **2x2 grid** for a high-level summary.
- Subplots include:
  1. **Monthly Total Line Chart**
  2. **Account Type Distribution (Bar Chart)**
  3. **Category Distribution (Pie Chart)**
  4. **Treemap** showing account and category balances for the latest month
     - Automatically adjusts **Liabilities** as negative values.
     - Displays hover info with labels, values, and percentages.
- Additional features:
  - Interactive **filters** are consistent across all tabs.
  - Hover and text formatting are preserved for clarity.
- **Use case:** Get an at-a-glance overview of your financial position, distributions, and detailed breakdowns in one view.

---

## Key Features
- Fully interactive charts using **Plotly**.
- **Dynamic filtering** by account type, category, and individual account.
- Download pivot tables in **Excel** format.
- Color-coded insights for quick assessment:
  - Green = positive growth
  - Red = negative growth
- Modular design with **4 tabs** for different analysis perspectives.

---

## Getting Started

Follow these steps to set up the environment and run the Streamlit app.

### 1. Clone the Repository (if needed)

```
git clone https://github.com/darshan-b/networth_tracker.git
cd networth_tracker
```

### 2. Create the Conda Environment

Make sure you have [Anaconda](https://www.anaconda.com/products/distribution) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) installed.

Create the environment from the provided `environment.yml` file:

```
conda env create -f env.yml
```

### 3. Activate the Environment

```
conda activate networth
```

### 4. Run the Streamlit App

```
streamlit run src\networth.py
```

The app will launch in your default web browser, typically at `http://localhost:8501`.
