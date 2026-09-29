"""
Stage 1 schema retrieval: keyword/table-name matching.

Scores each table by how many of the question's words match the
table name, its column names, or singular/plural variants of them.
Then expands the selected set to include any table connected via a
foreign key, so joins remain possible even when only one side of a
relationship matched keywords directly.

This is deliberately simple — no embeddings, no extra API calls. It
is a reasonable baseline and is what many production systems start
with before justifying the added complexity of semantic retrieval.
"""

import re

from app.ai.retriever_base import SchemaRetriever
from app.database.schema_models import DatabaseSchema

MIN_SCORE_THRESHOLD = 1
MAX_TABLES = 4


def _tokenize(text: str) -> set[str]:
    """Lowercase, strip punctuation, split into words, drop trivial words."""
    words = re.findall(r"[a-z]+", text.lower())
    stopwords = {"the", "a", "an", "of", "in", "for", "and", "or", "is", "are", "what", "how", "many"}
    return {w for w in words if w not in stopwords and len(w) > 2}


def _table_vocabulary(table_name: str, column_names: list[str]) -> set[str]:
    """
    Builds the set of words associated with a table: its name, its
    columns, and simple singular/plural variants (so 'product' matches
    a table named 'products' and vice versa).
    """
    vocab: set[str] = set()
    for word in [table_name] + column_names:
        # split snake_case into individual words too, e.g. "order_date" -> "order", "date"
        for part in word.split("_"):
            part = part.lower()
            vocab.add(part)
            if part.endswith("s"):
                vocab.add(part[:-1])  # "products" -> "product"
            else:
                vocab.add(part + "s")  # "product" -> "products"
    return vocab


class KeywordSchemaRetriever(SchemaRetriever):
    def retrieve(self, question: str, full_schema: DatabaseSchema) -> DatabaseSchema:
        question_tokens = _tokenize(question)

        scores: dict[str, int] = {}
        for table in full_schema.tables:
            column_names = [c.name for c in table.columns]
            vocab = _table_vocabulary(table.name, column_names)
            scores[table.name] = len(question_tokens & vocab)

        selected = {
            name for name, score in scores.items() if score >= MIN_SCORE_THRESHOLD
        }

        # Fallback: nothing scored — send everything rather than starving the LLM.
        if not selected:
            return full_schema

        # Keep only the top N by score if too many matched.
        if len(selected) > MAX_TABLES:
            ranked = sorted(selected, key=lambda n: scores[n], reverse=True)
            selected = set(ranked[:MAX_TABLES])

        selected = self._expand_via_foreign_keys(selected, full_schema)

        return full_schema.filter_to_tables(selected)

    def _expand_via_foreign_keys(self, selected: set[str], full_schema: DatabaseSchema) -> set[str]:
        """
        Adds any table connected to a selected table via a foreign key
        (in either direction), so joins the question implies remain
        possible even if only one side of the relationship matched
        keywords. E.g. "top products by revenue" matches `products`
        strongly but not `order_items` — yet the join needs both.
        """
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