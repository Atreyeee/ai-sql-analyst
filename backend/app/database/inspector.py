"""
Database schema introspection.

Uses SQLAlchemy's Inspector API to read table/column/key metadata
directly from Postgres's system catalogs (information_schema under
the hood), rather than hardcoding table definitions in Python.

This matters because as the schema evolves (new tables, new columns),
this module reflects that automatically — nothing to keep in sync
manually.
"""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.database.schema_models import (
    ColumnInfo,
    ForeignKeyInfo,
    TableInfo,
    DatabaseSchema,
)


def get_schema_info(engine: Engine) -> DatabaseSchema:
    """
    Introspects the connected database and returns a structured
    representation of every table: columns, types, primary keys,
    and foreign key relationships.
    """
    inspector = inspect(engine)
    tables: list[TableInfo] = []

    for table_name in inspector.get_table_names():
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_keys: list[str] = pk_constraint.get("constrained_columns", [])

        raw_columns = inspector.get_columns(table_name)
        columns = [
            ColumnInfo(
                name=col["name"],
                data_type=str(col["type"]),
                is_nullable=col["nullable"],
                is_primary_key=col["name"] in primary_keys,
            )
            for col in raw_columns
        ]

        foreign_keys = [
            ForeignKeyInfo(
                column=fk["constrained_columns"][0],
                references_table=fk["referred_table"],
                references_column=fk["referred_columns"][0],
            )
            for fk in inspector.get_foreign_keys(table_name)
        ]

        tables.append(
            TableInfo(
                name=table_name,
                columns=columns,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
            )
        )

    return DatabaseSchema(
        database_name=engine.url.database or "unknown",
        tables=tables,
    )


def schema_to_prompt_text(schema: DatabaseSchema) -> str:
    """
    Renders the structured schema as a compact text block suitable
    for inserting into an LLM prompt.

    We do NOT dump raw Python repr() or JSON here — LLMs parse
    concise, SQL-DDL-like text more reliably than nested JSON for
    this purpose. This function is what Phase 6 will actually use.
    """
    lines: list[str] = []
    for table in schema.tables:
        col_descriptions = ", ".join(
            f"{col.name} {col.data_type}" + (" PK" if col.is_primary_key else "")
            for col in table.columns
        )
        lines.append(f"Table {table.name}({col_descriptions})")

        for fk in table.foreign_keys:
            lines.append(
                f"  FK: {table.name}.{fk.column} -> {fk.references_table}.{fk.references_column}"
            )

    return "\n".join(lines)