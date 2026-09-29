"""
Prompt construction for LLM-based SQL generation.

Kept separate from llm_generator.py so you can iterate on wording
without touching orchestration logic, and so the exact prompt is
easy to inspect/version independently.
"""

SYSTEM_INSTRUCTION = """You are a SQL generation engine for a PostgreSQL analytics database.

Rules you MUST follow:
- Generate ONLY read-only SQL: a single SELECT or WITH statement.
- NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, or any other write/DDL statement, even if asked.
- NEVER generate more than one SQL statement.
- Only reference tables and columns that appear in the provided schema. Do not invent columns or tables.
- Use PostgreSQL syntax and functions (e.g. date_trunc, ILIKE).
- reasoning_summary must be one or two plain-English sentences only — do not include step-by-step internal reasoning.
"""


def build_user_prompt(question: str, schema_text: str) -> str:
    """
    Combines the user's question with schema context into the message
    sent to the model. Kept separate from SYSTEM_INSTRUCTION because
    the system instruction is static while this part changes per
    request (and will change shape again in Phase 7).
    """
    return f"""Database schema:
{schema_text}

User question: "{question}"

Generate the SQL query to answer this question, following all rules in the system instruction.
"""

def build_correction_prompt(
    question: str,
    schema_text: str,
    failed_sql: str,
    error_message: str,
) -> str:
    """
    Builds the user prompt for a SQL correction attempt. Includes the
    ORIGINAL question (not just "fix this SQL") so the model stays
    grounded in what it's actually trying to answer, not just in
    making the error message go away.
    """
    return f"""Database schema:
{schema_text}

User question: "{question}"

You previously generated this SQL, which failed:
{failed_sql}

The error was:
{error_message}

Generate a CORRECTED SQL query that answers the original question and
fixes this error. Follow all rules in the system prompt.
"""