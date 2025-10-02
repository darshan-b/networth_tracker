"""Data loading and preprocessing functions."""

import pandas as pd
import os


def load_data(filename="Networth.csv"):
    """Load and preprocess net worth data from CSV.
    
    Args:
        filename: Name of CSV file to load
        
    Returns:
        Preprocessed DataFrame with datetime Month column
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_path, "..", filename)
    
    data = pd.read_csv(csv_path)
    data['Month'] = pd.to_datetime(data['Month'])
    data['Amount'] = data['Amount'].round().astype(int)
    data['Month_Str'] = data['Month'].dt.strftime('%b-%Y')
    data = data.sort_values('Month')
    
    return data