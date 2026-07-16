"""
Tests for workflow/routing.py — task routing and retry decision logic.
"""

import pytest

from workflow.routing import route_tasks, should_retry, MAX_RETRIES


# ---------------------------------------------------------------------------
# route_tasks
# ---------------------------------------------------------------------------

def test_route_tasks_splits_sql_and_python():
    state = {
        "analysis_plan": [
            {"task_id": "t1", "description": "d1", "method": "sql"},
            {"task_id": "t2", "description": "d2", "method": "python"},
            {"task_id": "t3", "description": "d3", "method": "sql"},
        ],
        "errors": [],
    }
    result = route_tasks(state)
    assert len(result["sql_tasks"]) == 2
    assert len(result["python_tasks"]) == 1
    assert result["errors"] == []


def test_route_tasks_flags_invalid_method_as_error_not_silent_drop():
    state = {
        "analysis_plan": [
            {"task_id": "t1", "description": "d1", "method": "sql"},
            {"task_id": "t2", "description": "d2", "method": None},
            {"task_id": "t3", "description": "d3", "method": "excel"},
        ],
        "errors": [],
    }
    result = route_tasks(state)
    assert len(result["sql_tasks"]) == 1
    assert len(result["python_tasks"]) == 0
    assert len(result["errors"]) == 2
    assert "t2" in result["errors"][0]
    assert "t3" in result["errors"][1]


def test_route_tasks_preserves_existing_errors():
    state = {
        "analysis_plan": [{"task_id": "t1", "description": "d1", "method": "sql"}],
        "errors": ["a pre-existing error"],
    }
    result = route_tasks(state)
    assert "a pre-existing error" in result["errors"]


# ---------------------------------------------------------------------------
# should_retry
# ---------------------------------------------------------------------------

def test_should_retry_finalizes_when_approved():
    state = {"review": {"approved": True}, "retry_count": 0}
    assert should_retry(state) == "finalize"


def test_should_retry_retries_when_rejected_and_under_limit():
    state = {"review": {"approved": False}, "retry_count": 0}
    assert should_retry(state) == "retry"


def test_should_retry_finalizes_when_retries_exhausted():
    state = {"review": {"approved": False}, "retry_count": MAX_RETRIES}
    assert should_retry(state) == "finalize"


def test_should_retry_continues_when_no_review_present_yet():
    state = {"retry_count": 0}
    assert should_retry(state) == "retry"
