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
from app.analytics.result_analysis import analyze_result
from app.analytics.visualization import decide_chart_type, build_chart_config
from app.ai.explainer import generate_explanation
from app.ai.memory import get_or_create_session, reformulate_question, Turn
import time
from app.database.history_repository import insert_history_record, QueryHistoryRecord

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
    start_time = time.monotonic()
    session_id, history = get_or_create_session(request.session_id)
    standalone_question = reformulate_question(request.question, history)   
    full_schema = get_schema_info(get_engine())
    relevant_schema = _retriever.retrieve(request.question, full_schema)

    result = run_with_correction(request.question, relevant_schema, _generator)

    generated = result.generated
    execution = result.execution
    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    if not execution.success:
        insert_history_record(QueryHistoryRecord(
            session_id=session_id,
            question=request.question,
            standalone_question=standalone_question,
            sql_generated=generated.sql,
            execution_status="failed",
            execution_time_ms=elapsed_ms,
            row_count=None,
            correction_attempt_count=len(result.attempts),
            error_message=execution.error,
        ))
        return AskResponse(
            session_id=session_id,
            question=request.question,
            standalone_question=standalone_question,
            sql=generated.sql,
            reasoning_summary=generated.reasoning_summary,
            error=execution.error,
            correction_attempts=result.attempts,

        )
    analysis = analyze_result(execution.columns, execution.rows)
    chart_type = decide_chart_type(analysis)
    chart = build_chart_config(chart_type, execution.columns, execution.rows, analysis) if chart_type else None
    explanation = generate_explanation(standalone_question, generated.sql, execution.rows, analysis)
    history.add(Turn(
        question=request.question,
        standalone_question=standalone_question,
        sql=generated.sql,
        direct_answer=explanation.direct_answer,
    ))
    insert_history_record(QueryHistoryRecord(
        session_id=session_id,
        question=request.question,
        standalone_question=standalone_question,
        sql_generated=generated.sql,
        execution_status="success",
        execution_time_ms=elapsed_ms,
        row_count=execution.row_count,
        correction_attempt_count=len(result.attempts),
        error_message=None,
    ))
    return AskResponse(
        session_id=session_id,
        question=request.question,
        standalone_question=standalone_question,
        sql=generated.sql,
        reasoning_summary=generated.reasoning_summary,
        columns=execution.columns,
        rows=execution.rows,
        row_count=execution.row_count,
        truncated=execution.truncated,
        correction_attempts=result.attempts,
        analysis=analysis,
        chart=chart,
        explanation=explanation,
    )