"""
Stage 2 schema retrieval: embedding-based semantic matching.

Same SchemaRetriever interface as KeywordSchemaRetriever (Phase 7,
Stage 1) — this is a drop-in swap. Instead of literal word overlap,
this compares the MEANING of the question against a description of
each table, using vector embeddings and cosine similarity.

Table description embeddings are computed once and cached in memory,
since table descriptions don't change between requests — only the
question does.
"""

import numpy as np
from google import genai

from app.ai.retriever_base import SchemaRetriever
from app.database.config import settings
from app.database.schema_models import DatabaseSchema, TableInfo

EMBEDDING_MODEL = "gemini-embedding-001"
TOP_N_TABLES = 3
MIN_SIMILARITY = 0.3  # below this, we don't trust the match at all


def _table_description(table: TableInfo) -> str:
    """
    Builds a short natural-language description of a table for
    embedding. Richer than just the table name — includes column
    names so the embedding captures what kind of data lives there,
    which matters a lot for matching against varied question phrasing.
    """
    column_list = ", ".join(c.name for c in table.columns)
    return f"Table '{table.name}' with columns: {column_list}"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


class EmbeddingSchemaRetriever(SchemaRetriever):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        # Cache: table name -> embedding vector. Populated lazily on
        # first use, keyed off the schema's table names so a schema
        # change (new table) invalidates and rebuilds automatically.
        self._table_embeddings: dict[str, list[float]] = {}
        self._cached_table_names: set[str] = set()

    def _embed_text(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        return result.embeddings[0].values

    def _ensure_table_embeddings(self, full_schema: DatabaseSchema) -> None:
        """
        Computes and caches embeddings for every table description,
        but only for tables not already cached. This means a schema
        that grows by one table only costs one new embedding call,
        not a full recompute.
        """
        current_names = {t.name for t in full_schema.tables}
        if current_names == self._cached_table_names:
            return  # cache is already up to date

        for table in full_schema.tables:
            if table.name not in self._table_embeddings:
                description = _table_description(table)
                self._table_embeddings[table.name] = self._embed_text(description)

        self._cached_table_names = current_names

    def retrieve(self, question: str, full_schema: DatabaseSchema) -> DatabaseSchema:
        self._ensure_table_embeddings(full_schema)

        question_embedding = self._embed_text(question)

        scored = [
            (table.name, _cosine_similarity(question_embedding, self._table_embeddings[table.name]))
            for table in full_schema.tables
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)

        selected = {name for name, score in scored[:TOP_N_TABLES] if score >= MIN_SIMILARITY}

        # Fallback: nothing met the similarity bar — send everything
        # rather than starving the LLM of schema context (same
        # contract as Stage 1).
        if not selected:
            return full_schema

        selected = self._expand_via_foreign_keys(selected, full_schema)
        return full_schema.filter_to_tables(selected)

    def _expand_via_foreign_keys(self, selected: set[str], full_schema: DatabaseSchema) -> set[str]:
        """Identical logic to KeywordSchemaRetriever — kept local here
        rather than shared, since duplicating ~10 lines is simpler
        than introducing a shared utility module for one function at
        this project size. Worth revisiting if a third retriever needs it."""
        expanded = set(selected)
        tables_by_name = {t.name: t for t in full_schema.tables}

        for table_name in list(selected):
            table = tables_by_name.get(table_name)
            if table is None:
                continue
            for fk in table.foreign_keys:
                expanded.add(fk.references_table)

        for table in full_schema.tables:
            for fk in table.foreign_keys:
                if fk.references_table in selected:
                    expanded.add(table.name)

        return expanded