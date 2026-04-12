import pandas as pd

from app_constants import StockColumnNames
from data.loader import _normalize_stock_columns


def test_normalize_stock_columns_maps_symbol_to_ticker() -> None:
    df = pd.DataFrame(
        {
            ' Symbol ': ['AAPL'],
            'date': ['2026-01-01'],
            'quantity': [10],
            'Brokerage': ['Fidelity'],
            'Account Name': ['Taxable'],
            'Investment Type': ['Stock'],
        }
    )

    normalized = _normalize_stock_columns(df)

    assert StockColumnNames.TICKER in normalized.columns
    assert StockColumnNames.SYMBOL not in normalized.columns
    assert normalized.loc[0, StockColumnNames.TICKER] == 'AAPL'


def test_normalize_stock_columns_preserves_empty_dataframe() -> None:
    normalized = _normalize_stock_columns(pd.DataFrame())

    assert normalized.empty
