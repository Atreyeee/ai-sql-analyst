"""
Entry point for the AI SQL Analyst backend.

"""

from fastapi import FastAPI
from pydantic import BaseModel
from app.api import schema as schema_router
from app.api import query as query_router
from app.api import ask as ask_router
from app.api import history as history_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI SQL Analyst",
    description="Natural-language interface for querying a relational database.",
    version="0.1.0",
)
app.include_router(schema_router.router)
app.include_router(query_router.router)
app.include_router(ask_router.router)
app.include_router(history_router.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-sql-analyst")