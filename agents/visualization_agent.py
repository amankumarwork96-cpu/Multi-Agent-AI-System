"""
Visualization Agent
---------------------
Reads already-computed SQL and Python results and decides WHICH findings
deserve a chart and WHAT chart type fits. Never re-queries the dataset --
charts are built strictly from evidence that has already been computed
and validated by the SQL Agent / Python Analyst.

tools/chart_tool.py is solely responsible for actually rendering the
chart; this agent only decides whether to chart a result and how.
"""

import json
from groq import Groq
from pydantic import BaseModel, Field
from config import GROQ_API_KEY
from tools.chart_tool import generate_chart

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

VISUALIZATION_SYSTEM_PROMPT = """You are the Visualization Agent in a multi-agent data analysis system.

You will be given one already-computed analysis result (either SQL query
results or Python statistical output). Decide:
1. Whether this result is worth visualizing as a chart (some results,
   like a single correlation number or a two-group mean comparison,
   may not need a chart at all).
2. If yes, which chart type fits best, and its EXACT required parameters:

   - "bar_chart": one category column vs. one numeric value column.
     Required parameters (use these EXACT keys): "x_column", "y_column".

   - "grouped_bar_chart": two category columns vs. one numeric value
     column (e.g. Churn split across Contract types).
     Required parameters (use these EXACT keys): "x_column",
     "group_column", "y_column".
     Do NOT use "value_column" for this chart type.

   - "histogram": a single numeric column's distribution across many
     individual raw values (not aggregates).
     Required parameters (use this EXACT key): "value_column".
     Do NOT use "x_column", "y_column", or "group_column" for this
     chart type.

3. Set "parameters" using ONLY the exact keys listed above for your
   chosen chart_type -- never mix keys from different chart types.

STRICT RULES:
- Only reference column/key names that actually appear in the provided
  data. Never invent a column name.
- If the result has too few data points (e.g. a single row) or isn't
  suited to any of the three chart types, set "should_chart" to false.
- Return your answer strictly in the required structured JSON format.
"""

class ChartDecision(BaseModel):
    should_chart: bool
    chart_type: str = ""
    title: str = ""
    parameters: dict = Field(default_factory=dict)


def _decide_chart(task_id: str, result_data: list[dict]) -> ChartDecision:
    """Ask Groq whether/how to chart a single result's data."""
    # Only send a small sample to the LLM for decision-making -- it needs
    # to see column names and shape, not every row. The full result_data
    # is still used later when actually rendering the chart.
    sample_data = result_data[:10]
    truncated_note = (
        f"\n(Showing first 10 of {len(result_data)} total rows.)"
        if len(result_data) > 10
        else ""
    )

    user_message = f"""
Task ID: {task_id}

Already-computed result data sample (a list of row dicts):
{json.dumps(sample_data, indent=2)}{truncated_note}

Return your decision as JSON matching this exact schema:
{json.dumps(ChartDecision.model_json_schema(), indent=2)}
"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": VISUALIZATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},        
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw_content = response.choices[0].message.content

    try: 
        parsed_json = json.loads(raw_content)
        return ChartDecision(**parsed_json)
    except Exception as e:
        return ChartDecision(should_chart=False, title=f"Decision parsing failed: {e}")
    


def _flatten_python_result(result: dict) -> list[dict]:
    """
    Convert a Python tool result into flat row-style data suitable for
    charting. Most Python results (correlation, distribution_summary)
    are already flat single-row dicts and pass through unchanged.

    group_statistics results have this shape:
        {"numeric_column": ..., "group_column": ...,
         "groups": [{"<group_column>": ..., "mean": ..., "median": ..., "std": ...}, ...]}
    The "groups" list is already row-shaped -- just return it directly
    so each group becomes its own row instead of one giant nested "row".

    group_comparison results have this different nested shape:
        {"numeric_column": ..., "group_column": ...,
         "<group_a>": {"mean": ..., "count": ...},
         "<group_b>": {"mean": ..., "count": ...}}
    These get flattened into two rows, e.g.:
        [{"group": "<group_a>", "mean": ...}, {"group": "<group_b>", "mean": ...}]
    """
    if "groups" in result and isinstance(result["groups"], list):
        return result["groups"]

    if "group_column" in result and "numeric_column" in result:
        group_column = result["group_column"]
        reserved_keys = {"numeric_column", "group_column"}
        group_keys = [k for k in result if k not in reserved_keys]

        if group_keys and all(isinstance(result[k], dict) for k in group_keys):
            return [
                {group_column: group_key, **result[group_key]}
                for group_key in group_keys
            ]

    return [result]



def generate_visualizations(sql_results: list[dict], python_results: list[dict]) -> list[dict]:
    charts: list[dict]= []
    all_results = [
        (r["task_id"], r.get("data", [])) for r in sql_results if r.get("success")
    ] + [
        (r["task_id"], _flatten_python_result(r["result"])) for r in python_results if r.get("success")
    ]
    
    for task_id, data in all_results:
        if not data:
            continue

        decision = _decide_chart(task_id, data)

        if not decision.should_chart:
            continue

        chart_result = generate_chart(
            chart_type=decision.chart_type,
            data=data,
            title=decision.title,
            **decision.parameters,
        )

        charts.append(
            {
                "task_id": task_id,
                "chart_type": decision.chart_type,
                "title": decision.title,
                "success": chart_result["success"],
                "image_base64": chart_result.get("image_base64", ""),
                "error": chart_result.get("error")
            }
        )

    return charts