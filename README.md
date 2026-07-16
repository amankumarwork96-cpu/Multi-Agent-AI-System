# The Analyst's Case File — Multi-Agent AI Data Analyst

Upload a CSV or Excel dataset, ask a plain-language business question, and get a verified, evidence-backed report — complete with charts, a written executive summary, and a Reviewer agent that checks every claim against the real data before it's shown to you.

This is not a single LLM call wrapped in a chat box. It's a multi-agent pipeline where language models make *decisions* and deterministic code does all the actual *execution* — the LLM never touches your data directly.

---

## What it does

1. **Upload** a dataset (CSV or Excel).
2. **Ask** a business question in plain English (e.g. *"What factors are driving customer churn?"*).
3. Watch a pipeline of specialized agents work through the problem:
   - **Profiler** — inspects the dataset (rows, columns, types, missing values, likely target columns).
   - **Planner** — turns your question into a numbered analysis plan, grounded strictly in the real columns available.
   - **Router** — splits the plan into SQL-appropriate and statistics-appropriate tasks.
   - **SQL Agent** — writes real SQL, executed safely (read-only, injection-proof) via DuckDB.
   - **Python Analyst** — selects from a fixed menu of safe statistical operations (correlation, distribution summaries, group comparisons, outlier detection).
   - **Visualization Agent** — decides which findings deserve a chart, and what kind.
   - **Reporter** — synthesizes everything into an executive summary, key findings, recommendations, and limitations.
   - **Reviewer** — critically checks the report against the raw evidence: does it answer the question, is every claim supported, are there hallucinated columns, do recommendations actually follow from the findings? If not, it sends the report back for a **targeted retry** — only the report gets regenerated, not the whole pipeline.
4. **Get** a final report with charts, downloadable as a PDF, and saved to a local history you can revisit later.

---

## Architecture

The core design principle throughout: **agents decide, tools execute.**

An LLM is only ever allowed to *decide* what should happen — which SQL query answers a question, which statistical test fits, which chart type to use. It is never allowed to *directly execute* arbitrary code. Every action is carried out by a separate, deterministic, tested tool:

| Agent (decides) | Tool (executes) |
|---|---|
| SQL Agent | `tools/sql_tool.py` — validates and runs read-only SQL via DuckDB |
| Python Analyst | `tools/python_tool.py` — runs one of five fixed, safe statistical operations |
| Visualization Agent | `tools/chart_tool.py` — renders matplotlib charts from already-computed data |

This means the SQL Agent can never run `DROP TABLE`, the Python Analyst can never execute arbitrary code, and no agent ever queries the dataset more than once for the same evidence.

```
START
  → Profiler
  → Planner
  → Router
  → SQL Agent  ─┐
  → Python Analyst
  → Visualization Agent
  → Reporter
  → Reviewer
      ├─ approved      → END
      └─ needs revision → retry Reporter (max 2 attempts, then finalize anyway)
```

Built with **LangGraph** (workflow orchestration), **Groq / Llama** (LLM calls), **DuckDB** (safe SQL execution), **pandas** (statistics), **Streamlit** (UI), and **SQLite** (analysis history).

---

## Project structure

```
agents/            Reasoning agents (Profiler, Planner, SQL Agent, Python Analyst,
                    Visualization Agent, Reporter, Reviewer)
tools/              Deterministic execution (SQL Tool, Python Tool, Chart Tool)
prompts/            System prompts for each LLM-powered agent
schemas/            Pydantic models defining structured agent outputs
workflow/           LangGraph state, routing/retry logic, and the compiled graph
utils/              Shared helpers: data loading/cleaning, logging, PDF export,
                    SQLite history
ui/                 Streamlit application
tests/              Automated test suite (37 tests)
```

---

## Setup

```bash
git clone <your-repo-url>
cd multi-agent-ai-data-analyst
pip install -r requirements.txt
```

Create a `.env` file in the project root (see `.env.example`):

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free key at [console.groq.com/keys](https://console.groq.com/keys).

Run the app:

```bash
streamlit run ui/app.py
```

Run the test suite:

```bash
pytest tests/ -v
```

---

## A note on the free-tier API

This project runs on a free-tier Groq API key, which has a limited number of tokens per day and per minute. A single full analysis makes 6+ LLM calls (Planner, one call per SQL/Python task, one per chart decision, Reporter, Reviewer, plus any retries). If you see a "quota reached" message in the app, it's a temporary rate limit — not a bug — and it resolves on its own after a short wait.

---

## What this project demonstrates

This project was deliberately stress-tested against a second, structurally different dataset (a company layoffs dataset, alongside the original telco churn dataset) partway through development. That testing surfaced — and led to fixing — six distinct, real bugs:

1. SQL date-casting failures on non-ISO date formats (e.g. `3/6/2023`)
2. Oversized LLM prompts crashing on large raw SQL result sets
3. An unhandled nested data shape from one statistical operation
4. Oversized prompts in the Reporter
5. Oversized prompts in the Reviewer
6. A chart-rendering crash on missing (`None`) values during sorting

All are covered by the automated test suite so they can't silently regress. This is documented here deliberately: a system that only works on the dataset it was built against isn't demonstrating much — one that's been broken, diagnosed, and fixed against a genuinely different dataset is a stronger signal of engineering rigor.

---

## License

This is a personal portfolio project. Feel free to explore the code and adapt ideas from it.