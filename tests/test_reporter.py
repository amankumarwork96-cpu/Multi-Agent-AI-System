"""
Tests for the deterministic parts of agents/reporter.py --
specifically _truncate_data, which does not call any LLM.
"""

from agents.reporter import _truncate_data, MAX_EVIDENCE_ROWS


def test_truncate_leaves_small_data_untouched():
    data = [{"x": i} for i in range(5)]
    result = _truncate_data(data)
    assert result == data


def test_truncate_caps_large_data_and_adds_note():
    data = [{"x": i} for i in range(50)]
    result = _truncate_data(data)
    assert len(result) == MAX_EVIDENCE_ROWS + 1  # capped rows + one summary note
    assert result[:MAX_EVIDENCE_ROWS] == data[:MAX_EVIDENCE_ROWS]
    assert "_note" in result[-1]
    assert "50" in result[-1]["_note"]


def test_truncate_boundary_exactly_at_limit_is_untouched():
    """Exactly MAX_EVIDENCE_ROWS rows should NOT trigger truncation --
    only data strictly greater than the limit should be capped."""
    data = [{"x": i} for i in range(MAX_EVIDENCE_ROWS)]
    result = _truncate_data(data)
    assert result == data


def test_truncate_handles_empty_data():
    assert _truncate_data([]) == []