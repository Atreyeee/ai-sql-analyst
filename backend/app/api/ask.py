"""
The primary question-answering endpoint.

This wires together the full pipeline:
  schema retrieval -> SQL generation -> validation -> execution -> response

The SQL generator is injected as an interface (SQLGenerator), not
hardcoded to MockSQLGenerator, so Phase 6 can swap in a real LLM
by changing exactly one line.
"""
from app.ai.embedding_retriever import EmbeddingSchemaRetriever
from fastapi import APIRouter
from app.ai.llm_generator import LLMSQLGenerator
from app.ai.generator_base import SQLGenerator
from app.ai.mock_generator import MockSQLGenerator
from app.ai.pipeline_models import AskRequest, AskResponse
from app.database.connection import get_engine
from app.database.executor import execute_safe_sql
from app.database.inspector import get_schema_info
from app.database.config import settings
from app.ai.keyword_retriever import KeywordSchemaRetriever
from app.ai.retriever_base import SchemaRetriever
from app.ai.correction import run_with_correction
router = APIRouter(tags=["ask"])

# Single place where we decide which generator implementation is active.
# Phase 6 changes this one line to swap in the LLM-backed generator.
if settings.app_env == "test":
    _generator: SQLGenerator = MockSQLGenerator()
else:
    _generator: SQLGenerator = LLMSQLGenerator()

_retriever: SchemaRetriever = EmbeddingSchemaRetriever()

@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    full_schema = get_schema_info(get_engine())
    relevant_schema = _retriever.retrieve(request.question, full_schema)

    result = run_with_correction(request.question, relevant_schema, _generator)

    generated = result.generated
    execution = result.execution

    if not execution.success:
        return AskResponse(
            question=request.question,
            sql=generated.sql,
            reasoning_summary=generated.reasoning_summary,
            error=execution.error,
            correction_attempts=result.attempts,
        )

    return AskResponse(
        question=request.question,
        sql=generated.sql,
        reasoning_summary=generated.reasoning_summary,
        columns=execution.columns,
        rows=execution.rows,
        row_count=execution.row_count,
        truncated=execution.truncated,
        correction_attempts=result.attempts,
    )