"""
Python Analyst
---------------
Reads Python-routed analysis tasks and, for each one, asks Groq to choose
one safe predefined operation plus its parameters, grounded in the
dataset's real columns. The agent only decides WHICH operation and WHICH
columns -- tools/python_tool.py is solely responsible for computing it.
"""

import json
from groq import Groq
from config import GROQ_API_KEY
from prompts.analyst_prompt import ANALYST_SYSTEM_PROMPT
from tools.python_tool import run_python_operation
from schemas.analysis_schema import PythonOperationChoice, PythonTaskResult

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

def _choose_operation(
    task_id: str, task_description: str, dataset_profile: dict
) -> PythonOperationChoice:
    schema_hint = PythonOperationChoice.model_json_schema()

    user_message = f"""
Task ID: {task_id}
Analysis task:
{task_description}

Dataset profile:
{json.dumps(dataset_profile, indent=2)}

Return your decision as JSON matching this exact schema:
{json.dumps(schema_hint, indent=2)}
"""
    
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
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
            f"Python Analyst returned invalid JSON: {e}\nRaw response: {raw_content}"
        ) from e
    

    try:
        choice = PythonOperationChoice(**parsed_json)
    except Exception as e:
        raise ValueError(
            f"Python Analyst's JSON did not match PythonOperationChoice schema: {e}\nParsed JSON: {parsed_json}"
        ) from e
    
    return choice


def run_python_tasks(
        python_tasks: list[dict], dataset_profile: dict, dataset_path: str
) -> list[PythonTaskResult]:
    results: list[PythonTaskResult] = []

    for task in python_tasks:
        task_id = task["task_id"]
        description = task["description"]

        try:
            choice = _choose_operation(task_id, description, dataset_profile)
        except ValueError as e:
            results.append(
                PythonTaskResult(
                    task_id=task_id,
                    operation="unknown",
                    success=False,
                    error=str(e),
                )
            )
            continue

        tool_result = run_python_operation(
            dataset_path, choice.operation, **choice.parameters
        )

        results.append(
            PythonTaskResult(
                task_id=task_id,
                operation=choice.operation,
                success=tool_result["success"],
                result=tool_result.get("result", {}),
                error=tool_result.get("error")
            )
        )

    return results