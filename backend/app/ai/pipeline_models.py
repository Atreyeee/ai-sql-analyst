"""
Pydantic models shared across the question-answering pipeline.

Defining these once, in one place, means every stage (generator,
validator, executor, API layer) speaks the same typed structures —
no ad-hoc dicts passed between functions.
"""

from pydantic import BaseModel


class GeneratedSQL(BaseModel):
    """What any SQL generator (mock or LLM) must produce."""
    sql: str
    reasoning_summary: str
    tables_used: list[str]


class AskRequest(BaseModel):
    question: str

class CorrectionAttempt(BaseModel):
    """One retry attempt: what was tried and why it failed."""
    attempt_number: int
    failed_sql: str
    error: str


class AskResponse(BaseModel):
    question: str
    sql: str | None = None
    reasoning_summary: str | None = None
    columns: list[str] = []
    rows: list[dict] = []
    row_count: int = 0
    truncated: bool = False
    error: str | None = None
    correction_attempts: list[CorrectionAttempt] = []  