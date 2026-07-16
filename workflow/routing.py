"""
Task Router
------------
Splits the Planner's analysis_plan into sql_tasks and python_tasks based
on each task's declared method. Tasks with a missing or invalid method
are recorded in errors rather than silently dropped or defaulted — a
malformed method here almost always means a Planner prompt regression,
and we want that visible, not hidden.
"""

from workflow.state import AnalystState

VALID_METHODS = {"sql", "python"}


def route_tasks(state: AnalystState) -> dict:
    sql_tasks: list[dict] = []
    python_tasks: list[dict] = []
    routing_errors: list[str] = []

    for task in state["analysis_plan"]:
        method = task.get("method")

        if method == "sql":
            sql_tasks.append(task)
        elif method == "python":
            python_tasks.append(task)
        else:
            routing_errors.append(
                f"Task '{task.get('task_id', 'unknown')}' has invalid or "
                f"missing_method ({method!r}) and was not routed: "
                f"{task.get('description', 'no description')}"
            )

    existing_errors = state.get("errors", [])

    return {
        "sql_tasks": sql_tasks,
        "python_tasks": python_tasks,
        "errors": existing_errors + routing_errors,
    }


MAX_RETRIES = 2


def should_retry(state: AnalystState) -> str:
    """
    Decide whether to retry report generation or finalize the workflow,
    based on the Reviewer's verdict and the current retry count.

    Returns:
        "retry" if the report was rejected and retries remain.
        "finalize" if approved, or retries are exhausted.
    """
    review = state.get("review", {})
    approved = review.get("approved", False)
    retry_count = state.get("retry_count", 0)

    if approved:
        return "finalize"

    if retry_count >= MAX_RETRIES:
        return "finalize"

    return "retry"