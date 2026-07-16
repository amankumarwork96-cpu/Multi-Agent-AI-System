"""
Chart Tool
-----------
Deterministic chart generation from already-computed SQL/Python results.
No dataset re-querying and no LLM involvement happens here -- the
Visualization Agent decides WHICH result deserves a chart and WHAT type
fits; this tool only renders it.

Charts are returned as base64-encoded PNG strings so they can be stored
as plain data in the LangGraph state (no matplotlib objects in state)
and rendered directly in the Streamlit UI later (Phase 4).
"""

import base64
import io
import matplotlib
matplotlib.use("Agg")  # headless backend -- no display needed, safe for scripts/servers
import matplotlib.pyplot as plt

VALID_CHART_TYPES = {"bar_chart", "grouped_bar_chart", "histogram"}

def _fig_to_base64(fig) -> str:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches= "tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")

def _bar_chart(data: list[dict], x_column: str, y_column: str, title: str):
    labels = [str(row[x_column]) for row in data]
    values = [row[y_column] for row in data]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(labels, values, color='#4C72B0')
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)
    ax.set_title(title)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    return fig

def _grouped_bar_chart(data: list[dict], x_column: str, group_column: str, y_column: str, title: str):
    def normalize(value):
        return "Unknown" if value is None else str(value)

    categories = sorted({normalize(row[x_column]) for row in data})
    groups = sorted({normalize(row[group_column]) for row in data})

    pivot = {cat: {grp: 0 for grp in groups} for cat in categories}
    for row in data:
        cat = normalize(row[x_column])
        grp = normalize(row[group_column])
        pivot[cat][grp] = row[y_column]

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bar_width = 0.8 / len(groups)
    x_positions = range(len(categories))

    for i, grp in enumerate(groups):
        offsets = [x + i * bar_width for x in x_positions]
        values = [pivot[cat][grp] for cat in categories]
        ax.bar(offsets, values, width=bar_width, label=grp)

    ax.set_xticks([x + bar_width * (len(groups) - 1) / 2 for x in x_positions])
    ax.set_xticklabels(categories, rotation=30, ha="right")
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)
    ax.set_title(title)
    ax.legend(title=group_column)
    return fig


def _histogram(data: list[dict], value_column: str, title: str):
    values = [row[value_column] for row in data]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(values, bins=20, color='#55A868', edgecolor="white")
    ax.set_xlabel(value_column)
    ax.set_ylabel("Frequency")
    ax.set_title(title)
    return fig


def generate_chart(chart_type: str, data: list[dict], title: str, **kwargs) -> dict:
    if chart_type not in VALID_CHART_TYPES:
        return {
            "success": False,
            "error": f"Unknown chart_type '{chart_type}'. Valid types: {sorted(VALID_CHART_TYPES)}", 
        }
    if not data: 
        return {"success": False, "error": "No data provided to chart."}
    
    try:
        if chart_type == "bar_chart":
            fig = _bar_chart(data, title=title, **kwargs)
        elif chart_type == "grouped_bar_chart":
            fig = _grouped_bar_chart(data, title=title, **kwargs)
        elif chart_type == "histogram":
            fig = _histogram(data, title=title, **kwargs)
    except KeyError as e:
        return {"success": False, "error": f"Missing expected column in data: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Chart generation failed: {e}"}

    image_base64 = _fig_to_base64(fig)
    return {"success": True, "image_base64": image_base64}