"""
The primary question-answering endpoint.

This wires together the full pipeline:
  reformulation -> schema retrieval -> SQL generation (with correction)
  -> execution -> analysis -> visualization -> explanation -> response

The SQL generator is injected as an interface (SQLGenerator), not
hardcoded to a specific implementation, so swapping generators or
retrievers only ever requires changing the two lines below where
_generator and _retriever are instantiated.
"""

import time
import uuid

from fastapi import APIRouter

from app.ai.correction import run_with_correction
from app.ai.embedding_retriever import EmbeddingSchemaRetriever
from app.ai.explainer import generate_explanation
from app.ai.generator_base import SQLGenerator
from app.ai.llm_generator import LLMSQLGenerator
from app.ai.memory import Turn, get_or_create_session, reformulate_question
from app.ai.mock_generator import MockSQLGenerator
from app.ai.pipeline_models import AskRequest, AskResponse
from app.ai.retriever_base import SchemaRetriever
from app.analytics.result_analysis import analyze_result
from app.analytics.visualization import build_chart_config, decide_chart_type
from app.database.config import settings
from app.database.connection import get_engine
from app.database.history_repository import QueryHistoryRecord, insert_history_record
from app.database.inspector import get_schema_info
from app.observability.logger import log_event, timed_stage

router = APIRouter(tags=["ask"])

# Single place where we decide which generator/retriever implementation
# is active. Swapping either one is a one-line change here — nothing
# else in this file needs to know which concrete class is behind the
# interface.
if settings.app_env == "test":
    _generator: SQLGenerator = MockSQLGenerator()
else:
    _generator: SQLGenerator = LLMSQLGenerator()

_retriever: SchemaRetriever = EmbeddingSchemaRetriever()


@router.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    request_id = str(uuid.uuid4())
    log_event("request_start", request_id, question=request.question)
    start_time = time.monotonic()

    session_id, history = get_or_create_session(request.session_id)

    with timed_stage("reformulation", request_id):
        standalone_question = reformulate_question(request.question, history)

    full_schema = get_schema_info(get_engine())

    with timed_stage("retrieval", request_id):
        relevant_schema = _retriever.retrieve(standalone_question, full_schema)
    log_event(
        "retrieval_result",
        request_id,
        tables_selected=[t.name for t in relevant_schema.tables],
    )

    result = run_with_correction(
        standalone_question, relevant_schema, _generator, request_id=request_id
    )
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
        log_event(
            "request_end",
            request_id,
            success=False,
            correction_attempts=len(result.attempts),
        )
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
    chart = (
        build_chart_config(chart_type, execution.columns, execution.rows, analysis)
        if chart_type
        else None
    )

    explanation = generate_explanation(
        standalone_question, generated.sql, execution.rows, analysis
    )

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

    log_event(
        "request_end",
        request_id,
        success=True,
        correction_attempts=len(result.attempts),
    )

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