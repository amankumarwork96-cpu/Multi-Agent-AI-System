"""
Tests for tools/python_tool.py
"""

import pandas as pd
import pytest

from tools.python_tool import run_python_operation


@pytest.fixture
def sample_csv(tmp_path):
    data = {
        "Age": [25, 34, 45, 23, 39, 100],  # 100 is a deliberate outlier
        "TotalCharges": [100.5, 200.0, 250.0, 300.25, 150.0, 400.0],
        "Churn": ["Yes", "No", "No", "Yes", "No", "Yes"],
    }
    df = pd.DataFrame(data)
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_correlation_returns_valid_result(sample_csv):
    result = run_python_operation(
        sample_csv, "correlation", column_a="Age", column_b="TotalCharges"
    )
    assert result["success"] is True
    assert -1.0 <= result["result"]["correlation"] <= 1.0


def test_group_statistics_returns_all_groups(sample_csv):
    result = run_python_operation(
        sample_csv,
        "group_statistics",
        numeric_column="TotalCharges",
        group_column="Churn",
    )
    assert result["success"] is True
    groups = {g["Churn"] for g in result["result"]["groups"]}
    assert groups == {"Yes", "No"}


def test_distribution_summary_returns_expected_keys(sample_csv):
    result = run_python_operation(
        sample_csv, "distribution_summary", numeric_column="Age"
    )
    assert result["success"] is True
    for key in ["mean", "median", "std", "min", "max", "q1", "q3"]:
        assert key in result["result"]


def test_group_comparison_computes_both_groups(sample_csv):
    result = run_python_operation(
        sample_csv,
        "group_comparison",
        numeric_column="TotalCharges",
        group_column="Churn",
        group_a="Yes",
        group_b="No",
    )
    assert result["success"] is True
    assert "Yes" in result["result"]
    assert "No" in result["result"]


def test_group_comparison_with_nonexistent_group_fails_cleanly(sample_csv):
    result = run_python_operation(
        sample_csv,
        "group_comparison",
        numeric_column="TotalCharges",
        group_column="Churn",
        group_a="Maybe",
        group_b="No",
    )
    assert result["success"] is False
    assert "error" in result


def test_outlier_detection_finds_the_planted_outlier(sample_csv):
    """Age has one deliberate outlier (100) among values in the 20s-40s."""
    result = run_python_operation(sample_csv, "outlier_detection", numeric_column="Age")
    assert result["success"] is True
    assert result["result"]["outlier_count"] >= 1


def test_invalid_operation_name_fails_cleanly(sample_csv):
    result = run_python_operation(sample_csv, "not_a_real_operation")
    assert result["success"] is False
    assert "error" in result


def test_invalid_column_fails_cleanly(sample_csv):
    result = run_python_operation(sample_csv, "distribution_summary", numeric_column="NotReal")
    assert result["success"] is False
    assert "error" in result