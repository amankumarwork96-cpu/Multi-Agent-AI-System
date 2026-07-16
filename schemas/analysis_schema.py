"""
Analysis Result Schemas
------------------------
Defines the structured, validated shape of execution results coming back
from the SQL Agent and Python Analyst. Having one consistent shape for
"the outcome of a task" — regardless of which agent produced it — makes
it much simpler for the Reporter (Phase 3) to consume evidence uniformly.

Analysis tasks themselves (AnalysisTask) already live in
schemas/planner_schema.py — this file is specifically for results.
"""

from typing import Optional
from pydantic import BaseModel, Field

class SQLTaskResult(BaseModel):
    task_id: str
    query: str
    success: bool
    data: list[dict] = Field(default_factory=list)
    error: Optional[str] = None

class PythonTaskResult(BaseModel):
    task_id: str
    operation: str
    success: bool
    result: dict = Field(default_factory=dict)
    error: Optional[str] = None


class PythonOperationChoice(BaseModel):
    task_id: str
    operation: str
    parameters: dict = Field(default_factory=dict)