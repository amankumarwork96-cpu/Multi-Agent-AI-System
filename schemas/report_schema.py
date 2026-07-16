"""
Report Schema
--------------
Defines the exact structured output the Reporter Agent must return.
Matches the five-section structure defined in prompts/reporter_prompt.py,
so downstream consumers (Reviewer, Streamlit UI) can access each section
directly instead of parsing prose.
"""

from pydantic import BaseModel, Field

class KeyFindings(BaseModel):
    findings: str
    supporting_evidence: str
    task_id: str
    has_chart: bool = False


class BusinessReport(BaseModel):
    executive_summary: str
    key_findings: list[KeyFindings]
    business_recommendations: list[str]
    limitations: list[str] = Field(default_factory=list)