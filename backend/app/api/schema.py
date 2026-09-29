"""
Temporary endpoint to expose schema introspection for manual verification.
This will later be used internally by the AI pipeline rather than
exposed directly to end users, but for Phase 3 we expose it so you
can inspect the output yourself.
"""

from fastapi import APIRouter

from app.database.connection import get_engine
from app.database.inspector import get_schema_info, schema_to_prompt_text
from app.database.schema_models import DatabaseSchema

router = APIRouter(prefix="/schema", tags=["schema"])


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