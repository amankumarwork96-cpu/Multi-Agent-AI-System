"""
Python Tool
------------
Deterministic, safe statistical operations against the uploaded dataset.
This tool is the ONLY thing that ever runs pandas/numpy computations --
the Python Analyst agent only decides WHICH operation and WHICH columns
to use; this tool performs the actual calculation.

No arbitrary code is ever executed here. Every operation is a predefined,
fixed function -- the agent can only choose from this fixed menu.
"""

import pandas as pd

VALID_OPERATIONS = {
    "correlation",
    "group_statistics",
    "distribution_summary",
    "group_comparison",
    "outlier_detection",
}


def _to_numeric(df: pd.DataFrame, column: str) -> pd.Series:
    """
    Safely coerce a column to numeric, dropping values that can't convert
    (e.g. blank strings like ' ' in TotalCharges). Mirrors the same
    coercion logic already used in agents/profiler.py, applied here so
    every numeric operation is protected against the same data quality
    issue, not just the one that happened to surface first.
    """
    return pd.to_numeric(df[column], errors="coerce")


def _correlation(df: pd.DataFrame, column_a: str, column_b: str) -> dict:
    """Pearson correlation between two numeric columns."""
    series_a = _to_numeric(df, column_a)
    series_b = _to_numeric(df, column_b)
    corr_value = series_a.corr(series_b)
    return {"column_a": column_a, "column_b": column_b, "correlation": round(float(corr_value), 4)}


def _group_statistics(df: pd.DataFrame, numeric_column: str, group_column: str) -> dict:
    """Mean, median, and std of a numeric column, grouped by a categorical column."""
    numeric_series = _to_numeric(df, numeric_column)
    temp = pd.DataFrame({numeric_column: numeric_series, group_column: df[group_column]})
    grouped = temp.groupby(group_column)[numeric_column].agg(["mean", "median", "std"]).round(4)
    return {
        "numeric_column": numeric_column,
        "group_column": group_column,
        "groups": grouped.reset_index().to_dict(orient="records"),
    }


def _distribution_summary(df: pd.DataFrame, numeric_column: str) -> dict:
    """Summary statistics for a single numeric column."""
    series = _to_numeric(df, numeric_column).dropna()
    return {
        "column": numeric_column,
        "mean": round(float(series.mean()), 4),
        "median": round(float(series.median()), 4),
        "std": round(float(series.std()), 4),
        "min": round(float(series.min()), 4),
        "max": round(float(series.max()), 4),
        "q1": round(float(series.quantile(0.25)), 4),
        "q3": round(float(series.quantile(0.75)), 4),
    }


def _group_comparison(df: pd.DataFrame, numeric_column: str, group_column: str, group_a: str, group_b: str) -> dict:
    """Compare a numeric column's distribution between two specific groups."""
    numeric_series = _to_numeric(df, numeric_column)
    temp = pd.DataFrame({numeric_column: numeric_series, group_column: df[group_column]})

    series_a = temp.loc[temp[group_column] == group_a, numeric_column].dropna()
    series_b = temp.loc[temp[group_column] == group_b, numeric_column].dropna()

    if series_a.empty or series_b.empty:
        raise ValueError(
            f"One or both groups not found in column '{group_column}': "
            f"'{group_a}' ({len(series_a)} rows), '{group_b}' ({len(series_b)} rows)."
        )

    return {
        "numeric_column": numeric_column,
        "group_column": group_column,
        group_a: {"mean": round(float(series_a.mean()), 4), "count": int(series_a.count())},
        group_b: {"mean": round(float(series_b.mean()), 4), "count": int(series_b.count())},
    }


def _outlier_detection(df: pd.DataFrame, numeric_column: str) -> dict:
    """Flag outliers in a numeric column using the IQR method."""
    series = _to_numeric(df, numeric_column).dropna()
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outliers = series[(series < lower_bound) | (series > upper_bound)]

    return {
        "column": numeric_column,
        "lower_bound": round(float(lower_bound), 4),
        "upper_bound": round(float(upper_bound), 4),
        "outlier_count": int(outliers.count()),
        "outlier_percentage": round(float(outliers.count() / series.count() * 100), 2),
    }


def run_python_operation(dataset_path: str, operation: str, **kwargs) -> dict:
    """
    Execute a single safe, predefined Python operation against the dataset.

    Args:
        dataset_path: Path to the CSV file to load.
        operation: One of VALID_OPERATIONS.
        **kwargs: Column names and any other parameters the specific
            operation requires (e.g. numeric_column, group_column).

    Returns:
        On success: {"success": True, "result": {...}}
        On failure: {"success": False, "error": "..."}
    """
    if operation not in VALID_OPERATIONS:
        return {
            "success": False,
            "error": f"Unknown operation '{operation}'. Valid operations: {sorted(VALID_OPERATIONS)}",
        }

    try:
        df = pd.read_csv(dataset_path)
    except Exception as e:
        return {"success": False, "error": f"Failed to load dataset: {e}"}

    try:
        if operation == "correlation":
            result = _correlation(df, **kwargs)
        elif operation == "group_statistics":
            result = _group_statistics(df, **kwargs)
        elif operation == "distribution_summary":
            result = _distribution_summary(df, **kwargs)
        elif operation == "group_comparison":
            result = _group_comparison(df, **kwargs)
        elif operation == "outlier_detection":
            result = _outlier_detection(df, **kwargs)
    except KeyError as e:
        return {"success": False, "error": f"Column not found in dataset: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Operation failed: {e}"}

    return {"success": True, "result": result}