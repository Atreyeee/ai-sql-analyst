"""
Static SQL safety validation.

This module inspects a raw SQL string BEFORE it is ever sent to the
database and decides whether it is safe to execute. It is intentionally
strict and defense-in-depth: several independent checks, any of which
can reject the query. A more robust parser-based validator arrives in
Phase 8 — this phase uses careful string/regex analysis plus sqlparse
for statement splitting, which is sufficient once combined with the
read-only DB role as a backstop.
"""

import re
from dataclasses import dataclass

import sqlparse
from sqlparse.sql import Statement

# Statement types allowed to execute. Everything else is rejected.
ALLOWED_STATEMENT_KEYWORDS = {"SELECT", "WITH"}

# Keywords that indicate a write, DDL, or permissions operation.
# Checked as whole words anywhere in the (comment-stripped) SQL,
# not just at the start of the statement, to catch keywords hidden
# inside subqueries, CTEs, or appended via a second statement.
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "MERGE", "CALL", "EXECUTE",
    "COPY", "VACUUM", "REINDEX", "COMMENT", "SECURITY",
}

# Functions that don't modify data but can be abused for DoS,
# information disclosure, or reading arbitrary files.
DANGEROUS_FUNCTIONS = {
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir",
    "dblink", "dblink_connect", "lo_import", "lo_export",
    "pg_terminate_backend", "pg_cancel_backend", "current_setting",
    "set_config",
}


@dataclass
class ValidationResult:
    is_safe: bool
    reason: str | None = None


def _strip_comments(sql: str) -> str:
    """
    Removes SQL comments (-- line comments and /* block */ comments).

    This matters because a naive keyword search could be bypassed by
    hiding a real statement inside what LOOKS like a comment to a
    keyword scanner but isn't treated as a comment by the SQL engine
    in some contexts, or conversely, by using comments to break up
    a forbidden keyword (e.g. 'DR/**/OP'). We strip comments first
    so the checks below see the SQL the way Postgres would parse it.
    """
    sql = re.sub(r"--.*?(\n|$)", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def _split_statements(sql: str) -> list[Statement]:
    """
    Splits SQL text into individual statements using sqlparse.

    We use a real SQL-aware splitter instead of sql.split(';') because
    a semicolon can legitimately appear inside a string literal
    (e.g. WHERE name = 'Smith; Jones') — naive splitting would
    misfire on that.
    """
    return [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True) is not None]


def _get_statement_type(statement: Statement) -> str | None:
    first_token = statement.token_first(skip_cm=True)
    if first_token is None:
        return None
    return first_token.value.upper()


def validate_sql(raw_sql: str) -> ValidationResult:
    """
    Runs all safety checks against a raw SQL string.

    Returns ValidationResult(is_safe=False, reason=...) on the FIRST
    failure — we don't need to enumerate every problem, just refuse
    execution as soon as one is found.
    """
    if not raw_sql or not raw_sql.strip():
        return ValidationResult(is_safe=False, reason="Empty SQL is not allowed.")

    cleaned = _strip_comments(raw_sql)

    # --- Check 1: exactly one statement ---
    statements = _split_statements(cleaned)
    if len(statements) == 0:
        return ValidationResult(is_safe=False, reason="No valid SQL statement found.")
    if len(statements) > 1:
        return ValidationResult(
            is_safe=False,
            reason=f"Multiple SQL statements are not allowed ({len(statements)} found).",
        )

    statement = statements[0]

    # --- Check 2: statement type must be SELECT or WITH ---
    stmt_type = _get_statement_type(statement)
    if stmt_type is None or stmt_type.upper() not in ALLOWED_STATEMENT_KEYWORDS:
        return ValidationResult(
            is_safe=False,
            reason=f"Only SELECT/WITH statements are allowed (got: {stmt_type}).",
        )

    # --- Check 3: no forbidden keywords anywhere in the statement ---
    # This catches forbidden keywords even inside subqueries or CTEs,
    # e.g. "WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x"
    upper_cleaned = cleaned.upper()
    tokens = set(re.findall(r"[A-Z_]+", upper_cleaned))
    forbidden_found = tokens & FORBIDDEN_KEYWORDS
    if forbidden_found:
        return ValidationResult(
            is_safe=False,
            reason=f"Forbidden keyword(s) detected: {', '.join(sorted(forbidden_found))}",
        )

    # --- Check 4: no dangerous function calls ---
    lower_cleaned = cleaned.lower()
    dangerous_found = {
        fn for fn in DANGEROUS_FUNCTIONS if re.search(rf"\b{fn}\s*\(", lower_cleaned)
    }
    if dangerous_found:
        return ValidationResult(
            is_safe=False,
            reason=f"Dangerous function(s) detected: {', '.join(sorted(dangerous_found))}",
        )

    return ValidationResult(is_safe=True, reason=None)