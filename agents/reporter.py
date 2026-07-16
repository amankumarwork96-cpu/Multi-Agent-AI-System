"""
Reporter Agent
---------------
Synthesizes all executed SQL/Python evidence, plus chart availability,
into a structured BusinessReport answering the user's original question.
Never invents findings -- every claim must trace back to a real
task_id's evidence.
"""

import json
from groq import Groq
from config import GROQ_API_KEY
from prompts.reporter_prompt import REPORTER_SYSTEM_PROMPT
from schemas.report_schema import BusinessReport

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

MAX_EVIDENCE_ROWS = 15


def _truncate_data(data: list[dict]) -> list[dict]:
    """
    Cap the number of rows sent to the LLM. The Reporter needs enough
    real rows to ground specific claims and compute summaries, but not
    every row of a potentially large SELECT * result.
    """
    if len(data) > MAX_EVIDENCE_ROWS:
        return data[:MAX_EVIDENCE_ROWS] + [
            {"_note": f"... {len(data) - MAX_EVIDENCE_ROWS} more rows omitted for brevity, total {len(data)} rows"}
        ]
    return data


def _build_evidence_summary(
    sql_results: list[dict], python_results: list[dict], charts: list[dict]
) -> dict:
    """
    Assemble all execution evidence into one dict the Reporter can reason
    over, including which task_ids failed and which have charts. Large
    result sets are truncated to a representative sample to keep the
    prompt within model context/rate limits.
    """
    chart_task_ids = {c["task_id"] for c in charts if c.get("success")}

    sql_evidence = [
        {
            "task_id": r["task_id"],
            "success": r["success"],
            "query": r.get("query", ""),
            "data": _truncate_data(r.get("data", [])),
            "error": r.get("error"),
            "has_chart": r["task_id"] in chart_task_ids,
        }
        for r in sql_results
    ]

    python_evidence = [
        {
            "task_id": r["task_id"],
            "success": r["success"],
            "operation": r.get("operation", ""),
            "result": r.get("result", {}),
            "error": r.get("error"),
            "has_chart": r["task_id"] in chart_task_ids,
        }
        for r in python_results
    ]

    return {"sql_evidence": sql_evidence, "python_evidence": python_evidence}

def generate_report(
    user_question: str,
    dataset_profile: dict,
    sql_results: list[dict],
    python_results: list[dict],
    charts: list[dict],
    review_feedback: list[dict] | None = None,
) -> BusinessReport:
    evidence = _build_evidence_summary(sql_results, python_results, charts)
    schema_hint = BusinessReport.model_json_schema()

    user_message = f"""
User's original business question:
{user_question}

Dataset profile (for context):
{json.dumps(dataset_profile, indent=2)}

Executed evidence (SQL and Python results, including any failures and
chart availability):
{json.dumps(evidence, indent=2)}

Return your report as JSON matching this exact schema:
{json.dumps(schema_hint, indent=2)}
"""
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": REPORTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw_content = response.choices[0].message.content

    try:
        parsed_json = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Reporter returned invalid JSON: {e}\nRaw response: {raw_content}"
        ) from e
    
    try:
        report = BusinessReport(**parsed_json)
    except Exception as e:
        raise ValueError(
            f"Reporter's JSON did not match BusinessReport schema: {e}\nParsed JSON: {parsed_json}"
        ) from e

    return report