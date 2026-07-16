"""
Dataset Profiler
----------------
Reads a dataset and produces a structured summary that later agents
(Planner, SQL Agent, Python Analyst) will reason over.
"""

import pandas as pd
from utils.data_loading import load_and_clean_dataset

TARGET_KEYWORDS = [
    "churn", "target", "label", "class", "default",
    "fraud", "outcome", "status", "attrition", "response",
]


def profile_dataset(dataset_path: str) -> dict:
    df = load_and_clean_dataset(dataset_path)

    numerical_columns = df.select_dtypes(include="number").columns.tolist()
    categorical_columns = df.select_dtypes(exclude="number").columns.tolist()

    missing_pct = (df.isnull().mean() * 100).round(2)
    missing_values = {
        col: pct for col, pct in missing_pct.items() if pct > 0
    }

    binary_columns = [
        col for col in categorical_columns if df[col].nunique() == 2
    ]

   
    target_candidates = [
        col for col in binary_columns
        if any(keyword in col.lower() for keyword in TARGET_KEYWORDS)
    ]
    if not target_candidates:
        last_col = df.columns[-1]
        if last_col in binary_columns:
            target_candidates = [last_col]

    profile = {
        "rows": len(df),
        "columns": len(df.columns),
        "numerical_columns": numerical_columns,
        "categorical_columns": categorical_columns,
        "missing_values": missing_values,
        "binary_columns": binary_columns,
        "target_candidates": target_candidates,
    }

    return profile


if __name__ == "__main__":
    import json

    result = profile_dataset("data/WA_Fn-UseC_-Telco-Customer-Churn.csv")
    print(json.dumps(result, indent=2))