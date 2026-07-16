"""
Review Schema
--------------
Defines the exact structured output the Reviewer Agent must return.
The "approved" flag is what the workflow graph will branch on later in
this phase to decide whether to accept the report or trigger a targeted
retry.
"""

from pydantic import BaseModel, Field

class ReviewIssue(BaseModel):
    issue: str
    related_task_id: str = ""

class ReviewResult(BaseModel):
    approved: bool
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str