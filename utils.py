#utils.py

import pandas as pd


# ================= PROGRESS =================
def calc_progress(read_bytes, total_bytes):
    if total_bytes == 0:
        return 0
    return int((read_bytes / total_bytes) * 100)


# ================= SAFE NUMERIC CONVERSION =================
def convert_numeric(df, exclude=None):
    """
    Convert all dataframe columns to numeric except excluded ones
    """
    if exclude is None:
        exclude = []

    for col in df.columns:
        if col not in exclude:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ================= CHECK DIGITAL SIGNAL =================
def is_digital_series(series, threshold=5):
    """
    Detect digital signals (few unique values)
    """
    try:
        return series.nunique() <= threshold
    except:
        return False


# ================= SAFE COLUMN CHECK =================
def column_exists(df, column):
    return column in df.columns


# ================= SORT BY TIMESTAMP =================
def sort_by_time(df, column="Timestamp"):
    if column in df.columns:
        df = df.sort_values(column).reset_index(drop=True)
    return df


# ================= LIMIT ROWS FOR PLOTTING =================
def limit_rows(df, max_rows):
    """
    Downsample dataframe if too large for plotting
    """
    if len(df) > max_rows:
        step = len(df) // max_rows
        return df.iloc[::step]
    return df