"""
SQL Agent
----------
Reads SQL-routed analysis tasks and, for each one, asks Groq to generate
a real SQL query grounded in the dataset's actual columns. The agent
only decides WHAT query answers the task -- tools/sql_tool.py is solely
responsible for validating and executing it.
"""

import json
from groq import Groq
from config import GROQ_API_KEY
from prompts.sql_prompt import SQL_AGENT_SYSTEM_PROMPT
from tools.sql_tool import run_sql_query
from schemas.analysis_schema import SQLTaskResult

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

def _generate_sql_query(task_description: str, dataset_profile: dict) -> str:
    user_message = f"""
Analysis_task:
{task_description}

Dataset profile (the only real columns and facts you may use):
{json.dumps(dataset_profile, indent=2)}
"""
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SQL_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0,
    )

    raw_query = response.choices[0].message.content.strip()

    if raw_query.startswith("```"):
        raw_query = raw_query.strip("`")
        if raw_query.lower().startswith("sql"):
            raw_query = raw_query[3:].strip()

    return raw_query


def run_sql_tasks(
    sql_tasks: list[dict], dataset_profile: dict, dataset_path: str
) -> list[SQLTaskResult]:
    results: list[SQLTaskResult] = []

    for task in sql_tasks:
        task_id = task["task_id"]
        description = task["description"]

        query = _generate_sql_query(description, dataset_profile)

        if query == "NO_VALID_QUERY":
            results.append(
                SQLTaskResult(
                    task_id=task_id,
                    query="",
                    success=False,
                    error="Model determined this task cannot be answered with available columns.",
                )
            )
            continue

        tools_result = run_sql_query(dataset_path, query)

        results.append(
            SQLTaskResult(
                task_id=task_id,
                query=query,
                success=tools_result["success"],
                data=tools_result.get("data", []),
                error=tools_result.get("error"),
            )
        )

    return results