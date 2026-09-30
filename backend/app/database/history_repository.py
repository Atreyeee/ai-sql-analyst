"""
Persistence layer for query history.

Uses the MAIN application engine (read/write credentials), not the
restricted read-only executor engine from Phase 4/8 — this is the
one deliberate, narrow write path in the whole application, entirely
separate from anything LLM-generated SQL can reach.
"""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text

from app.database.connection import get_engine


class QueryHistoryRecord(BaseModel):
    id: int | None = None
    session_id: str
    question: str
    standalone_question: str
    sql_generated: str | None
    execution_status: str
    execution_time_ms: int | None
    row_count: int | None
    correction_attempt_count: int
    error_message: str | None
    created_at: datetime | None = None


def insert_history_record(record: QueryHistoryRecord) -> None:
    """
    Inserts one query history record. Failures here are logged but
    intentionally do NOT fail the parent /ask request — history is
    an observability concern, not core functionality. A user's
    question should still get answered even if history logging hiccups.
    """
    engine = get_engine()
    try:
        with engine.begin() as conn:  # begin() auto-commits on success
            conn.execute(
                text("""
                    INSERT INTO query_history
                        (session_id, question, standalone_question, sql_generated,
                         execution_status, execution_time_ms, row_count,
                         correction_attempt_count, error_message)
                    VALUES
                        (:session_id, :question, :standalone_question, :sql_generated,
                         :execution_status, :execution_time_ms, :row_count,
                         :correction_attempt_count, :error_message)
                """),
                {
                    "session_id": record.session_id,
                    "question": record.question,
                    "standalone_question": record.standalone_question,
                    "sql_generated": record.sql_generated,
                    "execution_status": record.execution_status,
                    "execution_time_ms": record.execution_time_ms,
                    "row_count": record.row_count,
                    "correction_attempt_count": record.correction_attempt_count,
                    "error_message": record.error_message,
                },
            )
    except Exception as e:
        # Deliberately swallow, not re-raise — see docstring.
        print(f"[history] Failed to record query history: {e}")


def get_recent_history(limit: int = 50) -> list[QueryHistoryRecord]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM query_history ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit},
        )
        return [QueryHistoryRecord(**dict(row._mapping)) for row in result]


def get_history_by_id(record_id: int) -> QueryHistoryRecord | None:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM query_history WHERE id = :id"), {"id": record_id}
        )
        row = result.fetchone()
        return QueryHistoryRecord(**dict(row._mapping)) if row else None