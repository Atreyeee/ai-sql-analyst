"""
Pydantic models representing a structured view of the database schema.

This is the data structure that will eventually be serialized into
the LLM prompt (Phase 6) and filtered by schema retrieval (Phase 7).
Keeping it as typed Pydantic models (not raw dicts) means every
consumer of schema info gets validation and autocomplete.
"""

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool


class ForeignKeyInfo(BaseModel):
    column: str
    references_table: str
    references_column: str


class TableInfo(BaseModel):
    name: str
    columns: list[ColumnInfo]
    primary_keys: list[str]
    foreign_keys: list[ForeignKeyInfo]


class DatabaseSchema(BaseModel):
    database_name: str
    tables: list[TableInfo]
    def filter_to_tables(self, table_names: set[str]) -> "DatabaseSchema":
        """
        Returns a new DatabaseSchema containing only the given tables.
        Used by schema retrieval to build the reduced schema sent to
        the LLM, without mutating the original full schema object.
        """
        return DatabaseSchema(
            database_name=self.database_name,
            tables=[t for t in self.tables if t.name in table_names],
        )