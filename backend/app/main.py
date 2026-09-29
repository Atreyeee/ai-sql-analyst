"""
Entry point for the AI SQL Analyst backend.

This file wires together the FastAPI application. In later phases,
API routes will move into backend/app/api/ as separate routers
(e.g. query.py, history.py), and this file will just assemble them.
For Phase 1, we keep everything here since there's only one endpoint.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="AI SQL Analyst",
    description="Natural-language interface for querying a relational database.",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Basic liveness check.

    Used to confirm the API process is running and responding to
    requests, independent of the database or any AI components
    (which don't exist yet). This is the kind of endpoint a load
    balancer or container orchestrator pings to decide if the
    service is healthy.
    """
    return HealthResponse(status="ok", service="ai-sql-analyst")