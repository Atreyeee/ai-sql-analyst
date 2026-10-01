"""
Safe SQL execution.

This module is the ONLY place in the application allowed to execute
LLM-generated or user-influenced SQL. It combines:

  1. Static validation (sql_safety.validate_sql)
  2. A dedicated read-only database connection
  3. A statement timeout
  4. A row limit on returned results

Even if validation somehow has a gap, the read-only role means
Postgres itself will reject any write.
"""
from app.observability.logger import log_event
from dataclasses import dataclass, field
from typing import Any
from app.database.schema_models import DatabaseSchema
from app.validation.schema_validation import validate_schema_references
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import time
from app.database.config import settings
from app.validation.sql_safety import validate_sql


MAX_ROWS = 1000
STATEMENT_TIMEOUT_MS = 5000  # also enforced at the DB role level (Phase 4 step 5)

_readonly_engine: Engine | None = None


def get_readonly_engine() -> Engine:
    """
    Singleton engine connected as the read-only database role.

    Deliberately a SEPARATE engine/connection pool from the main
    application engine (app.database.connection) — this one only
    ever uses the restricted DB user, so it can never accidentally
    execute a write even if application code elsewhere mixes things up.
    """
    global _readonly_engine
    if _readonly_engine is None:
        _readonly_engine = create_engine(
            settings.readonly_database_url,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
        )
    return _readonly_engine


@dataclass
class QueryExecutionResult:
    success: bool
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    error: str | None = None


def execute_safe_sql(raw_sql: str, schema: DatabaseSchema,request_id:str="unknown") -> QueryExecutionResult:
    """
    Validates and executes a SQL string against the given schema,
    returning structured results or a structured error.

    Two independent validation layers run before execution:
      1. validate_sql (Phase 4)         — security: statement type,
         multi-statement, forbidden keywords, dangerous functions.
      2. validate_schema_references (Phase 8) — correctness: every
         referenced table/column actually exists in `schema`.

    `schema` should be the same schema shown to the SQL generator —
    typically the retrieved subset from Phase 7, so validation checks
    the query against exactly what the LLM was told exists.
    """
    validation = validate_sql(raw_sql)
    if not validation.is_safe:
        return QueryExecutionResult(success=False, error=f"Rejected: {validation.reason}")

    schema_check = validate_schema_references(raw_sql, schema)
    if not schema_check.is_valid:
        return QueryExecutionResult(success=False, error=f"Rejected: {schema_check.reason}")

    engine = get_readonly_engine()
    start = time.monotonic()
    try:
        with engine.connect() as conn:
            conn.execute(text(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}"))
            result = conn.execute(text(raw_sql))
            columns = list(result.keys())
            fetched = result.fetchmany(MAX_ROWS + 1)
            truncated = len(fetched) > MAX_ROWS
            rows = [dict(zip(columns, row)) for row in fetched[:MAX_ROWS]]
            duration_ms = int((time.monotonic() - start) * 1000)
            log_event("sql_execution", request_id, duration_ms=duration_ms, row_count=len(rows), success=True)

            return QueryExecutionResult(
                success=True,
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
            )

    except SQLAlchemyError as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        log_event("sql_execution", request_id, duration_ms=duration_ms, success=False, error=str(e.__cause__ or e))
        return QueryExecutionResult(success=False, error=str(e.__cause__ or e))