"""
Reviewer Agent
---------------
Critically checks the Reporter's generated BusinessReport against the
real executed evidence -- not just for internal consistency, but for
factual grounding. This is the last verification step before a report
is considered final, and its "approved" flag drives the retry loop.
"""
from agents.reporter import _truncate_data
import json
from groq import Groq
from config import GROQ_API_KEY
from prompts.reviewer_prompt import REVIEWER_SYSTEM_PROMPT
from schemas.review_schema import ReviewResult

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

def review_reports(
    user_question: str,
    dataset_profile: dict,
    sql_results: list[dict],
    python_results: list[dict],
    report: dict,
) -> ReviewResult:
    schema_hint = ReviewResult.model_json_schema()

    truncated_sql_results = [
        {**r, "data": _truncate_data(r.get("data", []))} for r in sql_results
    ]

    user_message = f"""
User's original business question:
{user_question}

Dataset profile (real column names and types -- for checking against
hallucinated columns):
{json.dumps(dataset_profile, indent=2)}

Raw executed evidence:
SQL results:
{json.dumps(truncated_sql_results, indent=2)}

Python results:
{json.dumps(python_results, indent=2)}

Generated report to review:
{json.dumps(report, indent=2)}

Return your review as JSON matching this exact schema:
{json.dumps(schema_hint, indent=2)}
"""
    
    response = client.chat.completions.create(
        model= GROQ_MODEL,
        messages=[
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0
    )

    raw_content = response.choices[0].message.content

    try:
        parsed_json = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(
             f"Reviewer returned invalid JSON: {e}\nRaw response: {raw_content}"
        ) from e
        
    try:
        review = ReviewResult(**parsed_json)
    except Exception as e:
        raise ValueError(
            f"Reviewer's JSON did not match ReviewResult schema: {e}\nParsed JSON: {parsed_json}"
        ) from e

    return review