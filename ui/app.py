import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import base64
import tempfile

import groq as groq_sdk
import pandas as pd
import streamlit as st

from workflow.graph import build_graph
from utils.pdf_export import build_report_pdf
from utils.history_db import save_analysis, list_analyses, get_analysis


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="The Analyst's Case File",
    page_icon="\U0001F4C1",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
# Concept: a case file / evidence dossier. Agents gather evidence (SQL and
# statistical findings), the Reporter writes it up, and the Reviewer
# stamps a verdict -- APPROVED or NEEDS REVISION -- the way a senior
# investigator signs off on a junior analyst's file. Every dataset upload
# opens a new numbered case; every finding is an exhibit.

INK = "#1B2130"            # desk / background
INK_LINE = "#333D52"       # hairline rule on navy
PAPER = "#F1E9D8"          # main document surface
PAPER_RAISED = "#E7DCC2"   # secondary / recessed paper
PAPER_LINE = "#CFC2A0"     # hairline rule on paper
INK_TEXT = "#2A2417"       # body text on paper
LIGHT_TEXT = "#E9E2D2"     # body text on navy
MUTED_WARM = "#8C8368"     # captions on paper
MUTED_COOL = "#8A93AC"     # captions on navy
STAMP_RED = "#A6362C"      # verdict ink -- needs revision / alerts
SEAL_GREEN = "#3F6B58"     # verdict ink -- approved / progress
CLIP_GOLD = "#C98A2C"      # interactive accent -- buttons, links

NODE_LABELS = {
    "profiler": "Profile the dataset",
    "planner": "Draft the plan",
    "router": "Route the tasks",
    "sql_agent": "Pull SQL evidence",
    "python_analyst": "Run the statistics",
    "visualization": "Chart the findings",
    "reporter": "Write the file",
    "reviewer": "Review the file",
}
NODE_ORDER = list(NODE_LABELS.keys())

CUSTOM_CSS = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    html, body, .stApp {{
        background-color: {INK};
        color: {LIGHT_TEXT};
        font-family: 'Inter', sans-serif;
    }}

    h1, h2, h3, h4 {{
        font-family: 'Zilla Slab', serif !important;
        color: {LIGHT_TEXT} !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em;
    }}

    /* ---- case bar ---- */
    .case-bar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: {PAPER};
        border-radius: 3px;
        padding: 0.9rem 1.3rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 3px 0 {PAPER_LINE};
    }}
    .case-bar .case-id {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.1em;
        color: {MUTED_WARM};
        text-transform: uppercase;
    }}
    .case-bar .case-title {{
        font-family: 'Zilla Slab', serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: {INK_TEXT};
        margin-top: 0.1rem;
    }}
    .case-bar .case-status {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 0.3rem 0.7rem;
        border-radius: 2px;
        border: 1px solid currentColor;
    }}
    .status-idle {{ color: {MUTED_WARM}; }}
    .status-open {{ color: {CLIP_GOLD}; }}
    .status-closed {{ color: {SEAL_GREEN}; }}

    /* ---- checklist / pipeline ---- */
    .checklist {{
        background: {PAPER};
        border-radius: 3px;
        padding: 1rem 1.4rem;
        margin-bottom: 1.3rem;
        box-shadow: 0 3px 0 {PAPER_LINE};
    }}
    .checklist-caption {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.66rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: {MUTED_WARM};
        margin-bottom: 0.55rem;
    }}
    .checklist-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem 1.4rem;
    }}
    .checklist-item {{
        display: flex;
        align-items: center;
        gap: 0.45rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        color: {MUTED_WARM};
    }}
    .checklist-item .box {{
        width: 14px; height: 14px;
        border: 1.5px solid {MUTED_WARM};
        border-radius: 2px;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.62rem;
        flex-shrink: 0;
    }}
    .checklist-item.done {{ color: {INK_TEXT}; }}
    .checklist-item.done .box {{
        background: {SEAL_GREEN}; border-color: {SEAL_GREEN}; color: {PAPER};
    }}
    .checklist-item.active {{ color: {INK_TEXT}; font-weight: 600; }}
    .checklist-item.active .box {{
        border-color: {CLIP_GOLD};
        animation: boxpulse 1.2s infinite;
    }}
    @keyframes boxpulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(201,138,44,0.5); }}
        70% {{ box-shadow: 0 0 0 6px rgba(201,138,44,0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(201,138,44,0); }}
    }}
    @media (prefers-reduced-motion: reduce) {{
        .checklist-item.active .box {{ animation: none; }}
    }}

    /* ---- verdict stamp (signature element) ---- */
    .stamp-wrap {{
        display: flex;
        justify-content: center;
        padding: 1.4rem 0 0.6rem 0;
    }}
    .stamp {{
        font-family: 'Zilla Slab', serif;
        font-weight: 700;
        font-size: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        padding: 0.6rem 1.6rem;
        border: 3px solid;
        border-radius: 4px;
        transform: rotate(-5deg);
        display: inline-block;
        position: relative;
        opacity: 0.92;
    }}
    .stamp::after {{
        content: "";
        position: absolute;
        inset: 5px;
        border: 1px solid;
        border-color: inherit;
        border-radius: 2px;
    }}
    .stamp.approved {{ color: {SEAL_GREEN}; border-color: {SEAL_GREEN}; }}
    .stamp.revision {{ color: {STAMP_RED}; border-color: {STAMP_RED}; }}

    /* ---- paper cards ---- */
    .paper-card {{
        background: {PAPER};
        border-radius: 3px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 3px 0 {PAPER_LINE};
    }}
    .paper-card.recessed {{ background: {PAPER_RAISED}; box-shadow: none; }}
    .paper-card h3, .paper-card h4 {{ color: {INK_TEXT} !important; }}

    .eyebrow {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.66rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: {MUTED_WARM};
        margin-bottom: 0.4rem;
    }}

    /* plan / exhibit list */
    .exhibit-row {{
        display: flex;
        gap: 0.8rem;
        background: {PAPER};
        border-left: 3px solid {CLIP_GOLD};
        border-radius: 0 3px 3px 0;
        padding: 0.65rem 1rem;
        margin-bottom: 0.45rem;
        color: {INK_TEXT};
    }}
    .exhibit-row .tag {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        color: {MUTED_WARM};
        flex-shrink: 0;
    }}
    .exhibit-row .method {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        color: {SEAL_GREEN};
        margin-right: 0.4rem;
    }}

    /* findings / recs / limitations */
    .finding-card {{
        background: {PAPER};
        border-left: 3px solid {SEAL_GREEN};
        border-radius: 0 3px 3px 0;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.6rem;
        color: {INK_TEXT};
    }}
    .finding-card .evidence {{
        font-family: 'IBM Plex Mono', monospace;
        color: {MUTED_WARM};
        font-size: 0.76rem;
        margin-top: 0.35rem;
    }}
    .rec-card {{
        background: {PAPER};
        border-left: 3px solid {CLIP_GOLD};
        border-radius: 0 3px 3px 0;
        padding: 0.75rem 1.1rem;
        margin-bottom: 0.45rem;
        color: {INK_TEXT};
    }}
    .limitation-card {{
        background: {PAPER_RAISED};
        border-left: 3px solid {STAMP_RED};
        border-radius: 0 3px 3px 0;
        padding: 0.55rem 1rem;
        margin-bottom: 0.35rem;
        color: {MUTED_WARM};
        font-size: 0.86rem;
    }}

    /* alert / suspended-case card */
    .alert-card {{
        background: {PAPER};
        border: 2px dashed {STAMP_RED};
        border-radius: 4px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        color: {INK_TEXT};
    }}
    .alert-card .eyebrow {{ color: {STAMP_RED}; }}

    .empty-state {{
        border: 1px dashed {INK_LINE};
        border-radius: 4px;
        padding: 2.2rem;
        text-align: center;
        color: {MUTED_COOL};
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
    }}

    /* ---- sidebar ---- */
    section[data-testid="stSidebar"] {{
        background-color: #171C29;
        border-right: 1px solid {INK_LINE};
    }}
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {{
        font-family: 'Zilla Slab', serif !important;
        color: {CLIP_GOLD} !important;
        font-size: 1rem !important;
    }}
    section[data-testid="stSidebar"] label {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.68rem !important;
        color: {MUTED_COOL} !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .exhibit-tab {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.68rem;
        color: {MUTED_COOL};
        margin-bottom: 1px;
    }}
    .exhibit-tab .mark {{ font-weight: 700; margin-right: 0.35rem; }}

    /* buttons */
    .stButton > button {{
        background-color: {CLIP_GOLD};
        color: {INK};
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        border: none;
        border-radius: 3px;
        padding: 0.5rem 1rem;
    }}
    .stButton > button:hover {{ background-color: #DDA13F; color: {INK}; }}
    .stButton > button:disabled {{ background-color: {INK_LINE}; color: {MUTED_COOL}; }}
    .stDownloadButton > button {{
        background-color: transparent;
        border: 1px solid {SEAL_GREEN};
        color: {SEAL_GREEN};
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        border-radius: 3px;
    }}
    .stDownloadButton > button:hover {{ background-color: {SEAL_GREEN}; color: {PAPER}; }}

    /* metrics */
    div[data-testid="stMetric"] {{
        background-color: {PAPER_RAISED};
        border-radius: 3px;
        padding: 0.9rem;
    }}
    div[data-testid="stMetricLabel"] {{
        font-family: 'IBM Plex Mono', monospace;
        color: {MUTED_WARM};
        font-size: 0.7rem;
        text-transform: uppercase;
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'Zilla Slab', serif;
        color: {INK_TEXT};
    }}

    /* tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px;
        border-bottom: 1px solid {INK_LINE};
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent;
        color: {MUTED_COOL};
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        padding: 0.5rem 1rem;
        border-radius: 0;
    }}
    .stTabs [aria-selected="true"] {{
        color: {CLIP_GOLD} !important;
        border-bottom: 2px solid {CLIP_GOLD} !important;
        font-weight: 600;
    }}

    .streamlit-expanderHeader {{
        background-color: {PAPER_RAISED};
        color: {INK_TEXT};
        border-radius: 3px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_uploaded_file(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    temp_dir = tempfile.mkdtemp()

    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(uploaded_file)
        temp_path = Path(temp_dir) / "dataset.csv"
        df.to_csv(temp_path, index=False)
    else:
        temp_path = Path(temp_dir) / "dataset.csv"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    return str(temp_path)


def render_case_bar(status: str, dataset_name: str = "", case_no: int = 0) -> str:
    """status: 'idle' | 'open' | 'closed'"""
    status_class = {"idle": "status-idle", "open": "status-open", "closed": "status-closed"}[status]
    status_text = {"idle": "no case open", "open": "case open", "closed": "case closed"}[status]
    title = dataset_name if dataset_name else "Awaiting a dataset"
    case_id = f"CASE NO. {case_no:04d}" if case_no else "CASE NO. ----"
    return f"""
    <div class="case-bar">
        <div>
            <div class="case-id">{case_id}</div>
            <div class="case-title">{title}</div>
        </div>
        <div class="case-status {status_class}">{status_text}</div>
    </div>
    """


def render_checklist(active_node: str | None, done_nodes: set) -> str:
    items_html = []
    for node in NODE_ORDER:
        if node == active_node:
            state, mark = "active", "&hellip;"
        elif node in done_nodes:
            state, mark = "done", "&#10003;"
        else:
            state, mark = "", ""
        items_html.append(
            f'<div class="checklist-item {state}"><span class="box">{mark}</span>{NODE_LABELS[node]}</div>'
        )
    return f"""
    <div class="checklist">
        <div class="checklist-caption">Case progress</div>
        <div class="checklist-row">{''.join(items_html)}</div>
    </div>
    """


def render_stamp(approved: bool) -> None:
    label = "Approved" if approved else "Needs Revision"
    css_class = "approved" if approved else "revision"
    st.markdown(
        f'<div class="stamp-wrap"><div class="stamp {css_class}">{label}</div></div>',
        unsafe_allow_html=True,
    )


def render_alert(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="alert-card">
            <div class="eyebrow">Case suspended</div>
            <strong>{title}</strong>
            <p style="margin-top:0.5rem;">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dataset_profile(profile: dict) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", f"{profile['rows']:,}")
    col2.metric("Columns", profile["columns"])
    col3.metric("Target candidate(s)", ", ".join(profile["target_candidates"]) or "None found")

    with st.expander("Column details"):
        st.write("**Numerical columns:**", ", ".join(profile["numerical_columns"]) or "None")
        st.write("**Categorical columns:**", ", ".join(profile["categorical_columns"]) or "None")
        st.write("**Binary columns:**", ", ".join(profile["binary_columns"]) or "None")
        if profile["missing_values"]:
            st.write("**Missing values:**")
            for col, pct in profile["missing_values"].items():
                st.write(f"- {col}: {pct}%")


def render_analysis_plan(plan: list[dict]) -> None:
    for i, task in enumerate(plan, start=1):
        st.markdown(
            f"""
            <div class="exhibit-row">
                <span class="tag">EX. {i:02d}</span>
                <span><span class="method">[{task.get('method', '?')}]</span>{task['description']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_charts(charts: list[dict]) -> None:
    successful_charts = [c for c in charts if c.get("success")]
    if not successful_charts:
        st.markdown('<div class="empty-state">No charts were generated for this case.</div>', unsafe_allow_html=True)
        return

    cols = st.columns(2)
    for i, chart in enumerate(successful_charts):
        image_bytes = base64.b64decode(chart["image_base64"])
        with cols[i % 2]:
            st.image(image_bytes, caption=chart["title"], use_container_width=True)


def render_report(report: dict) -> None:
    """
    Renders a report's sections to the page. Purely a display function --
    no side effects -- safe to call for both a fresh analysis and a past
    case pulled from history.
    """
    st.subheader("Executive Summary")
    st.write(report["executive_summary"])

    st.subheader("Key Findings")
    for finding in report["key_findings"]:
        st.markdown(
            f"""
            <div class="finding-card">
                {finding['findings']}
                <div class="evidence">{finding['supporting_evidence']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Business Recommendations")
    for rec in report["business_recommendations"]:
        st.markdown(f'<div class="rec-card">{rec}</div>', unsafe_allow_html=True)

    if report["limitations"]:
        st.subheader("Limitations")
        for lim in report["limitations"]:
            st.markdown(f'<div class="limitation-card">{lim}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — exhibits (history) + new submission (input)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## Exhibits")
    past_analyses = list_analyses()

    if not past_analyses:
        st.markdown(
            f'<p style="font-family:\'IBM Plex Mono\',monospace; font-size:0.72rem; color:{MUTED_COOL};">'
            "No past cases filed yet.</p>",
            unsafe_allow_html=True,
        )
    else:
        for entry in past_analyses[:8]:
            mark_color = SEAL_GREEN if entry["approved"] else STAMP_RED
            mark_symbol = "&#10003;" if entry["approved"] else "!"
            label_text = entry["user_question"][:34] + ("…" if len(entry["user_question"]) > 34 else "")

            st.markdown(
                f"""
                <div class="exhibit-tab">
                    <span class="mark" style="color:{mark_color};">{mark_symbol}</span>
                    case #{entry['id']:04d} &middot; {entry['dataset_name']}
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(label_text, key=f"history_{entry['id']}", use_container_width=True):
                st.session_state["viewing_history_id"] = entry["id"]
                st.session_state.pop("full_state", None)
                st.session_state.pop("pipeline_error", None)
                st.rerun()

    st.markdown("---")

    st.markdown("## New Submission")
    uploaded_file = st.file_uploader("Dataset (csv or excel)", type=["csv", "xlsx", "xls"])

    if uploaded_file is not None:
        try:
            preview_df = (
                pd.read_excel(uploaded_file)
                if Path(uploaded_file.name).suffix.lower() in (".xlsx", ".xls")
                else pd.read_csv(uploaded_file)
            )
            uploaded_file.seek(0)
            with st.expander(f"Preview — {preview_df.shape[0]} rows x {preview_df.shape[1]} cols"):
                st.dataframe(preview_df.head(8), use_container_width=True, height=220)
        except Exception:
            pass

    user_question = st.text_area(
        "Business question",
        placeholder="e.g. which customer segments drove the Q3 revenue drop?",
        height=100,
    )
    run_clicked = st.button(
        "Open case & run analysis", type="primary",
        disabled=not (uploaded_file and user_question),
        use_container_width=True,
    )

    if "full_state" in st.session_state:
        if st.button("Close current case", use_container_width=True):
            del st.session_state["full_state"]
            st.session_state.pop("user_question", None)
            st.rerun()

    st.markdown("---")
    st.markdown(
        f'<p style="font-family:\'IBM Plex Mono\',monospace; font-size:0.7rem; color:{MUTED_COOL};">'
        "LangGraph &middot; Groq (Llama) &middot; DuckDB<br>"
        "Runs on a free-tier API key with a limited daily quota — "
        "if a case is suspended by a rate limit, please try again shortly.</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

case_bar_placeholder = st.empty()
checklist_placeholder = st.empty()

if run_clicked:
    dataset_name = uploaded_file.name
    case_bar_placeholder.markdown(render_case_bar("open", dataset_name), unsafe_allow_html=True)
    checklist_placeholder.markdown(render_checklist(None, set()), unsafe_allow_html=True)

    dataset_path = save_uploaded_file(uploaded_file)

    graph = build_graph()
    initial_state = {
        "dataset_path": dataset_path,
        "user_question": user_question,
        "errors": [],
        "retry_count": 0,
    }

    final_state = None
    done_nodes: set = set()
    pipeline_failed = False

    try:
        for step in graph.stream(initial_state, stream_mode="updates"):
            node_name = list(step.keys())[0]
            checklist_placeholder.markdown(render_checklist(node_name, done_nodes), unsafe_allow_html=True)
            final_state = {**(final_state or {}), **step[node_name]}
            done_nodes.add(node_name)

    except groq_sdk.RateLimitError:
        pipeline_failed = True
        st.session_state["pipeline_error"] = (
            "Daily or per-minute quota reached",
            "This demo runs on a free-tier Groq API key, which has a limited "
            "number of tokens per day and per minute. That quota has just been "
            "used up. Please try again in a little while — no data was lost, "
            "you can just re-run the same case once quota resets.",
        )
    except groq_sdk.APIStatusError:
        pipeline_failed = True
        st.session_state["pipeline_error"] = (
            "Request too large for the current model",
            "One step of the analysis produced more data than the language "
            "model could accept in a single request. This is usually transient "
            "-- please try a narrower business question, or try again shortly.",
        )
    except groq_sdk.APIError:
        pipeline_failed = True
        st.session_state["pipeline_error"] = (
            "The analysis service is temporarily unavailable",
            "There was a problem reaching the language model provider. Please "
            "wait a moment and try again.",
        )
    except Exception as e:
        pipeline_failed = True
        st.session_state["pipeline_error"] = (
            "The case could not be completed",
            f"An unexpected error interrupted the analysis: {e}",
        )

    if pipeline_failed:
        case_bar_placeholder.markdown(render_case_bar("idle", dataset_name), unsafe_allow_html=True)
        checklist_placeholder.markdown(render_checklist(None, done_nodes), unsafe_allow_html=True)
    else:
        checklist_placeholder.markdown(render_checklist(None, done_nodes), unsafe_allow_html=True)
        case_bar_placeholder.markdown(render_case_bar("closed", dataset_name), unsafe_allow_html=True)

        st.session_state["full_state"] = {**initial_state, **final_state}
        st.session_state["user_question"] = user_question
        st.session_state["dataset_name"] = dataset_name
        st.session_state.pop("viewing_history_id", None)
        st.session_state.pop("pipeline_error", None)

        # Save exactly once per completed run -- not inside render_report(),
        # which reruns on every tab switch / button click and would
        # otherwise create duplicate history entries.
        new_id = save_analysis(
            dataset_name=dataset_name,
            user_question=user_question,
            approved=final_state.get("review", {}).get("approved", False),
            final_report=final_state["final_report"],
        )
        st.session_state["case_no"] = new_id

elif "full_state" in st.session_state:
    case_bar_placeholder.markdown(
        render_case_bar("closed", st.session_state.get("dataset_name", ""), st.session_state.get("case_no", 0)),
        unsafe_allow_html=True,
    )
    checklist_placeholder.markdown(render_checklist(None, set(NODE_ORDER)), unsafe_allow_html=True)

else:
    case_bar_placeholder.markdown(render_case_bar("idle"), unsafe_allow_html=True)
    checklist_placeholder.markdown(render_checklist(None, set()), unsafe_allow_html=True)


if "pipeline_error" in st.session_state:
    title, message = st.session_state["pipeline_error"]
    render_alert(title, message)

if (
    "full_state" not in st.session_state
    and not run_clicked
    and "viewing_history_id" not in st.session_state
    and "pipeline_error" not in st.session_state
):
    st.markdown(
        '<div class="empty-state">Upload a dataset and enter a business question in the sidebar to open a case.</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Past-case viewer (takes priority over a stale in-session run)
# ---------------------------------------------------------------------------

if "viewing_history_id" in st.session_state:
    past = get_analysis(st.session_state["viewing_history_id"])
    if past:
        st.markdown(f"### Case #{past['id']:04d} — {past['dataset_name']}")
        st.caption(f"Filed {past['timestamp']} — {past['user_question']}")

        render_stamp(past["approved"])
        render_report(past["final_report"])

        pdf_bytes = build_report_pdf(past["final_report"], past["user_question"])
        st.download_button(
            label="Download case file (PDF)",
            data=pdf_bytes,
            file_name="analysis_report.pdf",
            mime="application/pdf",
            key="history_pdf_download",
        )

        if st.button("Close this exhibit"):
            del st.session_state["viewing_history_id"]
            st.rerun()


# ---------------------------------------------------------------------------
# Current-session report viewer
# ---------------------------------------------------------------------------

if "full_state" in st.session_state and "viewing_history_id" not in st.session_state:
    full_state = st.session_state["full_state"]
    review = full_state.get("review", {})

    tab_profile, tab_plan, tab_charts, tab_report = st.tabs(
        ["Profile", "Plan", "Exhibits", "Case File"]
    )

    with tab_profile:
        render_dataset_profile(full_state["dataset_profile"])

    with tab_plan:
        render_analysis_plan(full_state["analysis_plan"])

    with tab_charts:
        render_charts(full_state.get("charts", []))

    with tab_report:
        render_stamp(review.get("approved", False))
        render_report(full_state["final_report"])

        pdf_bytes = build_report_pdf(full_state["final_report"], st.session_state["user_question"])
        st.download_button(
            label="Download case file (PDF)",
            data=pdf_bytes,
            file_name="analysis_report.pdf",
            mime="application/pdf",
        )