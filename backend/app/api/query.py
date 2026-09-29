"""
Temporary manual-test endpoint for the safe SQL executor.
This lets us verify Phase 4 works end-to-end before any AI is involved.
In Phase 5+, this will be replaced by the full NL-question pipeline.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.database.executor import execute_safe_sql, QueryExecutionResult

router = APIRouter(prefix="/query", tags=["query"])


class RawSQLRequest(BaseModel):
    sql: str


@router.post("/raw", response_model=QueryExecutionResult)
def run_raw_sql(request: RawSQLRequest) -> QueryExecutionResult:
    """
    Accepts a raw SQL string and runs it through validation + safe execution.

    THIS ENDPOINT IS FOR DEVELOPMENT/TESTING ONLY. It exists so you can
    manually confirm the validator and executor behave correctly before
    an LLM is anywhere near this pipeline. It will not exist in this
    unprotected form once the real question-answering endpoint (Phase 5+)
    replaces it as the primary interface.
    """
    return execute_safe_sql(request.sql)