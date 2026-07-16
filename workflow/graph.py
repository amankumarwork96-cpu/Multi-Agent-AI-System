"""
Workflow Graph
--------------
Builds the LangGraph StateGraph connecting:
START -> Profiler -> Planner -> Router -> SQL Agent -> Python Analyst -> END

SQL Agent and Python Analyst run sequentially (not in parallel) for
simplicity -- they don't depend on each other's output, but sequential
execution avoids any state-merging complexity while the project is
still small. This can be revisited later if performance requires it.
"""
from utils.logging_config import get_logger

logger = get_logger(__name__)
from workflow.routing import route_tasks, should_retry
from agents.visualization_agent import generate_visualizations
from agents.reporter import generate_report
from agents.reviewer import review_reports
from langgraph.graph import StateGraph, START, END

from workflow.state import AnalystState
from agents.profiler import profile_dataset
from agents.planner import create_analysis_plan
from agents.sql_agent import run_sql_tasks
from agents.python_analyst import run_python_tasks


def profiler_node(state: AnalystState) -> dict:
    logger.info(f"Profiling dataset: {state['dataset_path']}")
    profile = profile_dataset(state["dataset_path"])
    return {"dataset_profile": profile}


def planner_node(state: AnalystState) -> dict:
    logger.info(f"Generating analysis plan for question: {state['user_question']}")
    plan = create_analysis_plan(
        user_question=state["user_question"],
        dataset_profile=state["dataset_profile"],
    )
    return {"analysis_plan": [task.model_dump() for task in plan.tasks]}


def router_node(state: AnalystState) -> dict:
    logger.info("Routing analysis tasks to SQL/Python agents")
    return route_tasks(state)


def sql_agent_node(state: AnalystState) -> dict:
    logger.info(f"Running {len(state['sql_tasks'])} SQL task(s)")
    results = run_sql_tasks(
        sql_tasks=state["sql_tasks"],
        dataset_profile=state["dataset_profile"],
        dataset_path=state["dataset_path"],
    )
    return {"sql_results": [r.model_dump() for r in results]}


def python_analyst_node(state: AnalystState) -> dict:
    logger.info(f"Running {len(state['python_tasks'])} Python task(s)")
    results = run_python_tasks(
        python_tasks=state["python_tasks"],
        dataset_profile=state["dataset_profile"],
        dataset_path=state["dataset_path"],
    )
    return {"python_results": [r.model_dump() for r in results]}



def visualization_node(state: AnalystState) -> dict:
    logger.info("Generating visualizations")
    charts = generate_visualizations(state["sql_results"], state["python_results"])
    return {"charts": charts}


def reporter_node(state: AnalystState) -> dict:
    logger.info(f"Generating report (retry_count={state.get('retry_count', 0)})")
    review = state.get("review")
    review_feedback = review["issues"] if review and not review.get("approved", True) else None

    report = generate_report(
        user_question=state["user_question"],
        dataset_profile=state["dataset_profile"],
        sql_results=state["sql_results"],
        python_results=state["python_results"],
        charts=state["charts"],
        review_feedback=review_feedback,
    )

    updates = {"draft_report": report.model_dump()}
    if review_feedback is not None:
        updates["retry_count"] = state.get("retry_count", 0) + 1
    return updates


def reviewer_node(state: AnalystState) -> dict:
    
    review = review_reports(
        user_question=state["user_question"],
        dataset_profile=state["dataset_profile"],
        sql_results=state["sql_results"],
        python_results=state["python_results"],
        report=state["draft_report"],
    )
    
    logger.info(f"Review result: approved={review.approved}, issues={len(review.issues)}")
    
    updates = {"review": review.model_dump()}

    # Finalize the report if approved, OR if we've exhausted retries --
    # we still return the best available report rather than nothing.
    if review.approved or state.get("retry_count", 0) >= 2:
        updates["final_report"] = state["draft_report"]

    return updates


def build_graph():
    graph_builder = StateGraph(AnalystState)

    graph_builder.add_node("profiler", profiler_node)
    graph_builder.add_node("planner", planner_node)
    graph_builder.add_node("router", router_node)
    graph_builder.add_node("sql_agent", sql_agent_node)
    graph_builder.add_node("python_analyst", python_analyst_node)
    graph_builder.add_node("visualization", visualization_node)
    graph_builder.add_node("reporter", reporter_node)
    graph_builder.add_node("reviewer", reviewer_node)

    graph_builder.add_edge(START, "profiler")
    graph_builder.add_edge("profiler", "planner")
    graph_builder.add_edge("planner", "router")
    graph_builder.add_edge("router", "sql_agent")
    graph_builder.add_edge("sql_agent", "python_analyst")
    graph_builder.add_edge("python_analyst", "visualization")
    graph_builder.add_edge("visualization", "reporter")
    graph_builder.add_edge("reporter", "reviewer")

    graph_builder.add_conditional_edges(
        "reviewer",
        should_retry,
        {"retry": "reporter", "finalize": END},
    )

    return graph_builder.compile()