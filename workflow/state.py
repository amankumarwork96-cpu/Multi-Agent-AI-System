"""
Shared Workflow State
----------------------
Defines the single state object that flows through every node in the
LangGraph workflow.

Phase 2: added sql_results and python_results to hold the validated
execution outcomes from the SQL Agent and Python Analyst.
"""

from typing import TypedDict


class AnalystState(TypedDict):
    
    dataset_path: str
    user_question: str
    dataset_profile: dict
    analysis_plan: list[dict]
    sql_tasks: list[dict]
    python_tasks: list[dict]
    errors: list[str]
    sql_results: list[dict]
    python_results: list[dict]
    charts: list[dict]
    draft_report: dict
    review: dict
    retry_count: int
    final_report: dict