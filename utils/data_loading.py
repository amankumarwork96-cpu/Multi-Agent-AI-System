"""
Data Loading
-------------
Shared dataset loading and cleaning logic used by both the Profiler and
the SQL Tool, so they always agree on column types for the same file.

This exists because the Profiler and SQL Tool previously loaded the same
CSV independently -- the Profiler coerced corrupted-numeric columns
(e.g. TotalCharges, which has a few blank-string entries) to numeric,
but the SQL Tool did not. That mismatch caused DuckDB to treat such
columns as VARCHAR, breaking aggregate queries like AVG(TotalCharges)
even though the Profiler correctly reported the column as numeric.
"""

import pandas as pd


def load_and_clean_dataset(dataset_path: str) -> pd.DataFrame:
    """
    Load a CSV and coerce any column that is "mostly numeric" (a few
    corrupted/blank entries aside) into an actual numeric dtype.

    A column is reclassified as numeric only if SOME (not ALL) of its
    values fail to convert -- that pattern means a few corrupted entries
    in an otherwise numeric column. If every value fails, the column is
    genuinely categorical and is left untouched.

    Args:
        dataset_path: Path to the CSV file to load.

    Returns:
        A cleaned DataFrame with corrupted-numeric columns coerced.
    """
    df = pd.read_csv(dataset_path)

    categorical_columns = df.select_dtypes(exclude="number").columns.tolist()

    for col in categorical_columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        original_nulls = df[col].isnull().sum()
        new_nulls = converted.isnull().sum()

        if new_nulls > original_nulls and new_nulls < len(df):
            df[col] = converted

    return df