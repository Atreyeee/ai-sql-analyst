"""
Parser-based SQL validation: checks that every table and column
referenced in a query actually exists in the given schema.

This catches a class of error Phase 4's regex/keyword validator
cannot: a syntactically valid, perfectly "safe" SELECT statement
that references a hallucinated or filtered-out table/column. Since
Phase 7 sends the LLM only a RETRIEVED SUBSET of the schema, this
also catches the case where the model somehow references a table it
was never shown at all.
"""

from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from app.database.schema_models import DatabaseSchema


@dataclass
class SchemaValidationResult:
    is_valid: bool
    reason: str | None = None


def _parse_or_none(sql: str) -> exp.Expression | None:
    """
    Parses SQL into a sqlglot AST. Returns None (rather than raising)
    on a parse failure — schema validation isn't responsible for
    catching syntax errors; that's Phase 4's job and, as a backstop,
    Postgres's job at execution time. If we can't parse it, we let it
    proceed to execution, where a real syntax error will surface
    clearly rather than us guessing at a confusing secondary error here.
    """
    try:
        return sqlglot.parse_one(sql, read="postgres")
    except Exception:
        return None


def _extract_referenced_tables(ast: exp.Expression) -> set[str]:
    """
    Walks the AST and collects every table name referenced anywhere
    in the query — including tables inside subqueries, CTEs, and JOINs.
    sqlglot's find_all(exp.Table) does this traversal for us; we don't
    write our own tree-walking logic.
    """
    return {table.name for table in ast.find_all(exp.Table)}


def _extract_referenced_columns(ast: exp.Expression) -> set[str]:
    """
    Walks the AST and collects every column name referenced anywhere
    in the query (SELECT list, WHERE, GROUP BY, ORDER BY, JOIN
    conditions, etc). We intentionally do NOT try to resolve which
    table each column belongs to — with aliases, multi-table JOINs,
    and computed expressions, reliable resolution is a much harder
    problem. Instead we check each column name against the UNION of
    all columns across all referenced tables, which is a looser but
    much more robust check: it correctly allows valid columns and
    still catches genuinely made-up column names.
    """
    return {col.name for col in ast.find_all(exp.Column)}


def validate_schema_references(sql: str, schema: DatabaseSchema) -> SchemaValidationResult:
    """
    Checks that every table and column referenced in the SQL exists
    somewhere in the given schema. `schema` should be whatever schema
    was actually shown to the LLM (the retrieved subset from Phase 7),
    since that's the contract the model was given.
    """
    ast = _parse_or_none(sql)
    if ast is None:
        # Can't validate references without a parse tree — defer to
        # execution-time error handling (Phase 9) instead of blocking here.
        return SchemaValidationResult(is_valid=True, reason=None)

    known_tables = {table.name for table in schema.tables}
    known_columns = {
        col.name for table in schema.tables for col in table.columns
    }

    referenced_tables = _extract_referenced_tables(ast)
    unknown_tables = referenced_tables - known_tables
    if unknown_tables:
        return SchemaValidationResult(
            is_valid=False,
            reason=f"Query references unknown table(s): {', '.join(sorted(unknown_tables))}",
        )

    referenced_columns = _extract_referenced_columns(ast)
    unknown_columns = referenced_columns - known_columns
    if unknown_columns:
        return SchemaValidationResult(
            is_valid=False,
            reason=f"Query references unknown column(s): {', '.join(sorted(unknown_columns))}",
        )

    return SchemaValidationResult(is_valid=True, reason=None)