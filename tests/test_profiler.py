"""
Tests for agents/profiler.py

Uses small, hand-crafted temporary CSVs instead of the real Telco dataset
so tests are fast, self-contained, and independent of file location.
"""

import pandas as pd
import pytest
from agents.profiler import profile_dataset

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


def test_profile_returns_correct_row_and_column_counts(sample_csv):
    profile = profile_dataset(sample_csv)
    assert profile["rows"] == 5
    assert profile["columns"] == 4

def test_profile_coerces_corrupted_numeric_column(sample_csv):
    profile = profile_dataset(sample_csv)
    assert "TotalCharges" in profile["numerical_columns"]
    assert "TotalCharges" not in profile["categorical_columns"]

def test_profile_keeps_genuine_categorical_column_untouched(sample_csv):
    profile = profile_dataset(sample_csv)
    assert "Gender" in profile["categorical_columns"]
    assert "Gender" not in profile["numerical_columns"]

def test_profile_detects_missing_values(sample_csv):
    profile = profile_dataset(sample_csv)
    assert "TotalCharges" in profile["missing_values"]
    assert profile["missing_values"]["TotalCharges"] > 0


def test_profile_detects_binary_columns(sample_csv):
    profile = profile_dataset(sample_csv)
    assert "Gender" in profile["binary_columns"]
    assert "Churn" in profile["binary_columns"]


def test_profile_finds_target_candidate_via_keyword(sample_csv):
    """Churn matches a target keyword, so it should be picked over Gender."""
    profile = profile_dataset(sample_csv)
    assert profile["target_candidates"] == ["Churn"]