"""
Tests for the deterministic parts of agents/visualization_agent.py --
specifically _flatten_python_result, which does not call any LLM.
"""

from agents.visualization_agent import _flatten_python_result


def test_flatten_passes_through_simple_result_unchanged():
    """correlation/distribution_summary results are already flat --
    should pass through as a single-row list."""
    result = {"column_a": "MonthlyCharges", "column_b": "TotalCharges", "correlation": 0.65}
    flattened = _flatten_python_result(result)
    assert flattened == [result]


def test_flatten_handles_group_statistics_shape():
    """group_statistics nests multiple groups under a 'groups' key --
    each group should become its own top-level row."""
    result = {
        "numeric_column": "TotalCharges",
        "group_column": "Churn",
        "groups": [
            {"Churn": "Yes", "mean": 100.0, "median": 90.0, "std": 10.0},
            {"Churn": "No", "mean": 200.0, "median": 190.0, "std": 15.0},
        ],
    }
    flattened = _flatten_python_result(result)
    assert flattened == result["groups"]
    assert len(flattened) == 2


def test_flatten_handles_group_comparison_shape():
    """group_comparison nests two named groups as separate dict values --
    these should be flattened into two rows keyed by the group column."""
    result = {
        "numeric_column": "tenure",
        "group_column": "Churn",
        "Yes": {"mean": 17.98, "count": 1869},
        "No": {"mean": 37.57, "count": 5174},
    }
    flattened = _flatten_python_result(result)
    assert len(flattened) == 2
    assert {"Churn": "Yes", "mean": 17.98, "count": 1869} in flattened
    assert {"Churn": "No", "mean": 37.57, "count": 5174} in flattened


def test_flatten_does_not_misfire_on_plain_dict_with_similar_keys():
    """A result that happens to have a 'group_column' key but whose other
    values are plain numbers (not dicts) should NOT be treated as a
    group_comparison shape -- it should pass through unchanged."""
    result = {"group_column": "Contract", "numeric_column": "tenure", "some_other_stat": 42}
    flattened = _flatten_python_result(result)
    assert flattened == [result]