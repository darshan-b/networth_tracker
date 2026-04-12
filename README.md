# Personal Finance Tracker

This project is a Streamlit app for exploring three parts of a personal finance workflow from one place:

- `Net Worth Tracker` for balance trends and breakdowns
- `Expense Tracker` for transactions, budgets, insights, and cash flow
- `Stock Tracker` for portfolio history and analysis

The app is organized around local files in the repo, so the fastest way to get started is to place your data in the expected folders, create the environment, and run the Streamlit entry point.

## Project Structure

Key files and folders:

- `app.py` - main Streamlit entry point
- `data/loader.py` - data loading and preprocessing
- `data/raw/` - net worth, transaction, and stock input files
- `data/` - optional budget files
- `ui/views/` - view-level Streamlit pages and dashboards

## Expected Data Files

The current app looks for these files by default:

### Required for Net Worth Tracker

- `data/raw/Networth.csv`

Expected columns:

- `month`
- `amount`
- `account_type`
- `category`

### Required for Expense Tracker

- `data/raw/transactions.xlsx`

Expected columns include:

- `date`
- `amount`
- `category`
- `merchant`
- `account`

Notes:

- If a `type` column is missing, the loader adds a default `expense` value.

### Optional for Budgets

The app will try these files in order:

1. `data/budgets.csv`
2. `data/budgets.xlsx`

Expected columns:

- `date`
- `budget`

If no budget file is found, the app falls back to hard-coded default budget values in [data/loader.py](/c:/Users/darsh/Documents/GitHub/networth_tracker/data/loader.py).

### Required for Stock Tracker

- `data/raw/stock_positions.xlsx`

Expected sheets:

- `trading_log`
- `Historical_Tracking`

The stock tracker expects historical data with columns such as:

- `Date`
- `ticker` or `Symbol`
- `quantity`
- `Brokerage`
- `Account Name`
- `Investment Type`

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/darshan-b/networth_tracker.git
cd networth_tracker
```

### 2. Create the environment

This repo includes an environment file named `env.yml`:

```bash
conda env create -f env.yml
```

### 3. Activate the environment

```bash
conda activate networth
```

### 4. Add your data files

Place your local data files in the expected locations:

- `data/raw/Networth.csv`
- `data/raw/transactions.xlsx`
- `data/raw/stock_positions.xlsx`
- optional: `data/budgets.csv` or `data/budgets.xlsx`

### 5. Run the app

Use the current Streamlit entry point:

```bash
streamlit run app.py
```

The app usually opens at `http://localhost:8501`.

## What You'll See

### Net Worth Tracker

- header filters for `account_type` and `category`
- sidebar account filtering
- net worth over time
- summarized table
- dashboard
- growth projections
- data explorer

### Expense Tracker

- date-based filtering
- overview
- transactions
- budgets
- insights
- sankey chart

### Stock Tracker

- brokerage, account, and investment-type filters
- date range filtering
- overview
- performance
- allocation
- risk analysis
- transactions
- cost basis

## Common First-Run Issues

- If a page says data is missing, confirm the file name and location match the paths above exactly.
- If the stock tracker does not load, verify both the workbook name and sheet names.
- If budgets do not appear, check whether your budget file is in `data/` instead of `data/raw/`.
- If Streamlit fails to start, confirm the environment was created from `env.yml` and activated before running `streamlit run app.py`.

## Developer Checks

This repo now includes a lightweight tooling baseline in `pyproject.toml`.

Run lint checks:

```bash
ruff check .
```

Run tests:

```bash
pytest
```

Optional formatting:

```bash
ruff format .
```
