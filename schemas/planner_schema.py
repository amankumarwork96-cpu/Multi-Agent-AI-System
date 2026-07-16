"""
Planner Schema
---------------
Defines the exact structured output the Planner Agent must return.

Using Pydantic here means Groq's structured output mode can validate the
LLM's response against this shape directly — no fragile text parsing.
Downstream agents (Router, SQL Agent, Python Analyst in Phase 2) will
consume this same structure, so its shape is a shared contract.
"""

from typing import Optional
from pydantic import BaseModel, Field

class AnalysisTask(BaseModel):
    """
    A single analytical step the Planner wants investigated.

    Fields:
        task_id: Unique identifier for this task (e.g. "task_1").
        description: Plain-language description of what should be analyzed.
        method: Optional hint about how this task should eventually be
            executed (e.g. "sql" or "python"). Left optional in Phase 1
            since no execution agents exist yet — this becomes more
            important once Phase 2 adds the Router.
    """

    task_id: str = Field(..., description="Unique ID for this task, e.g. 'task_1'.")
    description: str = Field(
        ..., description="Clear, specific description of what to analyze."
    )
    method: Optional[str] = Field(
        default=None,
        description="Optional hint for how this task should be executed later (e.g. 'sql', 'python').",
    )
    

class AnalysisPlan(BaseModel):
    """
    The full structured output returned by the Planner Agent.

    Fields:
        tasks: Ordered list of AnalysisTask objects representing the
            full analysis plan for the user's question.
    """

    tasks: list[AnalysisTask] = Field(
        ..., description="Ordered list of analysis tasks needed to answer the user's question."
    )