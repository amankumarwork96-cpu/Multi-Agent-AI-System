"""
SQL Tool
---------
Deterministic, safe SQL execution against the uploaded dataset using
DuckDB. This tool is the ONLY thing that ever touches the database —
the SQL Agent only decides what query to run; this tool decides
whether it's safe and actually runs it.

The dataset is always registered under the fixed table name "dataset",
regardless of the original filename, so agents/prompts never need to
know the real file name.
"""

import re
import duckdb
from utils.data_loading import load_and_clean_dataset

TABLE_NAME = "dataset"

FORBIDDEN_KEYWORDDS = [
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "attach", "detech", "copy", "pragma", "install", "load"
]

def _is_safe_select(query: str) -> tuple[bool, str]:
    stripped = query.strip().rstrip(";").strip()

    if not stripped:
        return False, "Query is empty."
    
    if not stripped.lower().startswith("select"):
        return False, "Only SELECT queries are allowed."
    
    lowered = stripped.lower()
    for keyword in FORBIDDEN_KEYWORDDS:
        if re.search(rf"\b{keyword}\b", lowered):
            return False, f"Query contains forbidden keyword: '{keyword}'."
        
    if ";" in query.strip().rstrip(";"):
        return False, "Multiple statements are not allowed."
    
    return True, ""

def run_sql_query(dataset_path: str, query: str) -> dict:
    is_safe, reason = _is_safe_select(query)
    if not is_safe:
        return {"success": False, "error": f"Rejected unsafe query: {reason}"}
    
    try:
        df = load_and_clean_dataset(dataset_path)
    except Exception as e:
        return {"success": False, "error": f"Failed to load dataset: {e}"}


    try:
        con = duckdb.connect()
        con.register(TABLE_NAME, df)
        result_df = con.execute(query).fetchdf()
        con.close()
    except Exception as e:
        return {"success": False, "error": f"SQL execution failed: {e}"}
    
    return {"success": True, "data": result_df.to_dict(orient="records")}