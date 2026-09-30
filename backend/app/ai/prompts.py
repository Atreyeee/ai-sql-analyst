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

EXPLANATION_SYSTEM_INSTRUCTION = """You are a data analyst explaining a SQL query result to a business user.

CRITICAL RULE: You must NOT state any number, statistic, or figure that
is not explicitly present in the provided analysis or row sample. Do
NOT calculate, estimate, or infer new numbers. If you want to mention
a percentage change or comparison that isn't already computed for you,
describe it qualitatively (e.g. "December was notably higher than
November") instead of inventing a precise number.

Do not expose your internal reasoning process — respond only with the
final structured explanation.

Respond in this structure:
- direct_answer: one or two sentences directly answering the user's question
- key_findings: 2-4 short bullet points of notable facts from the data
- caveats: 0-2 short notes about limitations (e.g. missing data, small
  sample size, truncated results) — only include if genuinely relevant,
  do not invent a caveat if there isn't one
"""


def build_explanation_prompt(
    question: str,
    sql: str,
    analysis_summary: str,
    row_sample_text: str,
) -> str:
    return f"""Original question: "{question}"

SQL used to answer it:
{sql}

Verified statistical summary of the result (these numbers are already
computed and correct — use them directly, do not recompute):
{analysis_summary}

Sample of the actual result rows (for context only):
{row_sample_text}

Write the explanation now, following the structure and rules in the system instruction.
"""