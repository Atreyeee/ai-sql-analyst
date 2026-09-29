"""
Temporary endpoint to expose schema introspection for manual verification.
This will later be used internally by the AI pipeline rather than
exposed directly to end users, but for Phase 3 we expose it so you
can inspect the output yourself.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.ai.keyword_retriever import KeywordSchemaRetriever
from app.database.connection import get_engine
from app.database.inspector import get_schema_info, schema_to_prompt_text
from app.database.schema_models import DatabaseSchema
from app.ai.embedding_retriever import EmbeddingSchemaRetriever

_debug_retriever = EmbeddingSchemaRetriever()
router = APIRouter(prefix="/schema", tags=["schema"])

class RetrievalDebugRequest(BaseModel):
    question: str

@router.get("", response_model=DatabaseSchema)
def get_schema() -> DatabaseSchema:
    """Returns the structured schema of the connected database."""
    engine = get_engine()
    return get_schema_info(engine)


@router.get("/prompt-text")
def get_schema_prompt_text() -> dict:
    """Returns the schema rendered as prompt-ready text (Phase 6 preview)."""
    engine = get_engine()
    schema = get_schema_info(engine)
    return {"prompt_text": schema_to_prompt_text(schema)}

@router.post("/retrieval-debug", response_model=DatabaseSchema)
def retrieval_debug(request: RetrievalDebugRequest) -> DatabaseSchema:
    """
    Shows exactly which tables the retriever selected for a given
    question, without calling the LLM. Useful for tuning MIN_SCORE_THRESHOLD
    and MAX_TABLES, and for demonstrating retrieval behavior directly.
    """
    engine = get_engine()
    full_schema = get_schema_info(engine)
    return _debug_retriever.retrieve(request.question, full_schema)