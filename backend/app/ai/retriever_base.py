"""
Interface for schema retrieval implementations.

Same pattern as SQLGenerator (Phase 5): define the contract first,
implement it multiple ways, and let the rest of the pipeline depend
only on the interface. This is what lets us swap keyword matching
for embeddings later without touching api/ask.py.
"""

from abc import ABC, abstractmethod

from app.database.schema_models import DatabaseSchema


class SchemaRetriever(ABC):
    @abstractmethod
    def retrieve(self, question: str, full_schema: DatabaseSchema) -> DatabaseSchema:
        """
        Given a question and the FULL database schema, return a
        DatabaseSchema containing only the subset of tables relevant
        to answering the question.

        Implementations must always return a valid DatabaseSchema
        (never empty if the full schema is non-empty) — if nothing
        scores above threshold, fall back to returning everything
        rather than starving the LLM of schema context entirely.
        """
        raise NotImplementedError