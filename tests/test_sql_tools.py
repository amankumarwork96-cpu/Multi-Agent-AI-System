"""
Tests for tools/sql_tool.py
"""

import pandas as pd
import pytest

from tools.sql_tool import run_sql_query


@pytest.fixture
def sample_csv(tmp_path):
    data = {
        "Age": [25, 34, 45, 23, 39],
        "TotalCharges": ["100.5", "", "250.0", "300.25", "150.0"],
        "Gender": ["Male", "Female", "Male", "Female", "Male"],
        "Churn": ["Yes", "No", "No", "Yes", "No"],
    }
    df = pd.DataFrame(data)
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_valid_select_query_succeeds(sample_csv):
    result = run_sql_query(sample_csv, "SELECT COUNT(*) as total FROM dataset")
    assert result["success"] is True
    assert result["data"][0]["total"] == 5


def test_group_by_query_returns_expected_groups(sample_csv):
    result = run_sql_query(
        sample_csv, "SELECT Gender, COUNT(*) as count FROM dataset GROUP BY Gender"
    )
    assert result["success"] is True
    genders = {row["Gender"] for row in result["data"]}
    assert genders == {"Male", "Female"}


def test_aggregate_on_corrupted_numeric_column_works(sample_csv):
    """Regression test for the bug where TotalCharges (numeric with blank
    entries) was loaded as VARCHAR by the SQL Tool and broke AVG()."""
    result = run_sql_query(
        sample_csv, "SELECT AVG(TotalCharges) as avg_charges FROM dataset"
    )
    assert result["success"] is True
    assert result["data"][0]["avg_charges"] is not None


def test_drop_statement_is_rejected(sample_csv):
    result = run_sql_query(sample_csv, "DROP TABLE dataset")
    assert result["success"] is False
    assert "error" in result


def test_delete_statement_is_rejected(sample_csv):
    result = run_sql_query(sample_csv, "DELETE FROM dataset WHERE Age > 30")
    assert result["success"] is False


def test_multiple_statements_are_rejected(sample_csv):
    result = run_sql_query(
        sample_csv, "SELECT * FROM dataset; DROP TABLE dataset;"
    )
    assert result["success"] is False


def test_empty_query_is_rejected(sample_csv):
    result = run_sql_query(sample_csv, "")
    assert result["success"] is False


def test_invalid_column_returns_clean_error_not_crash(sample_csv):
    result = run_sql_query(sample_csv, "SELECT NotARealColumn FROM dataset")
    assert result["success"] is False
    assert "error" in result