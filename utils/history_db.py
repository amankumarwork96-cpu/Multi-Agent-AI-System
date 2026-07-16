"""
Analysis History
------------------
Local SQLite persistence for completed analyses, so past reports can be
browsed later instead of disappearing when the Streamlit session ends.
No server or external database needed -- just a local file.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data") / "history.db"
DB_PATH.parent.mkdir(exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the analysis_history table if it doesn't already exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                dataset_name TEXT NOT NULL,
                user_question TEXT NOT NULL,
                approved INTEGER NOT NULL,
                final_report TEXT NOT NULL
            )
            """
        )


def save_analysis(dataset_name: str, user_question: str, approved: bool, final_report: dict) -> int:
    """
    Save one completed analysis to history.

    Args:
        dataset_name: Original uploaded filename (for display purposes).
        user_question: The business question that was asked.
        approved: Whether the Reviewer approved the final report.
        final_report: The final_report dict (BusinessReport shape).

    Returns:
        The new row's id.
    """
    init_db()
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analysis_history
                (timestamp, dataset_name, user_question, approved, final_report)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                dataset_name,
                user_question,
                1 if approved else 0,
                json.dumps(final_report),
            ),
        )
        return cursor.lastrowid


def list_analyses() -> list[dict]:
    """
    List all past analyses, most recent first (without the full report
    body, to keep this lightweight for a history list view).
    """
    init_db()
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp, dataset_name, user_question, approved
            FROM analysis_history
            ORDER BY id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_analysis(analysis_id: int) -> dict | None:
    """Fetch one past analysis's full report by id, or None if not found."""
    init_db()
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_history WHERE id = ?", (analysis_id,)
        ).fetchone()
        if row is None:
            return None

        result = dict(row)
        result["final_report"] = json.loads(result["final_report"])
        result["approved"] = bool(result["approved"])
        return result