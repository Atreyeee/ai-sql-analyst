"""
Bounded SQL self-correction loop.

Orchestrates: generate -> validate/execute -> (if failed and
retryable) regenerate with error context -> validate/execute again,
up to a fixed number of attempts.

This module owns the RETRY POLICY. It does not know how to generate
SQL or execute it — it depends on the same SQLGenerator interface
(Phase 5) and execute_safe_sql (Phase 4/8), calling them as building
blocks. This keeps the retry logic testable independently of any
particular LLM or database.
"""

from dataclasses import dataclass, field
from app.ai.llm_retry import call_gemini_with_retry
from app.ai.generator_base import SQLGenerator
from app.ai.pipeline_models import CorrectionAttempt, GeneratedSQL
from app.ai.prompts import build_correction_prompt, SYSTEM_INSTRUCTION  
from app.database.executor import QueryExecutionResult, execute_safe_sql
from app.database.schema_models import DatabaseSchema
from app.database.config import settings
from google import genai
from google.genai import types
from app.ai.llm_generator import RESPONSE_SCHEMA, MODEL_NAME
from app.database.inspector import schema_to_prompt_text
import json
MAX_CORRECTION_ATTEMPTS = 2  # total retries AFTER the initial attempt

# Error substrings that indicate a security rejection (Phase 4).
# These are NOT retried the same way — see _is_retryable below.
_SECURITY_REJECTION_MARKERS = (
    "Only SELECT/WITH statements are allowed",
    "Multiple SQL statements are not allowed",
    "Forbidden keyword(s) detected",
    "Dangerous function(s) detected",
)


@dataclass
class CorrectionLoopResult:
    generated: GeneratedSQL
    execution: QueryExecutionResult
    attempts: list[CorrectionAttempt] = field(default_factory=list)


def _is_retryable(error: str) -> bool:
    """
    Decides whether a failure is worth asking the LLM to fix.

    Security rejections (Phase 4) are deliberately excluded: if the
    model generated a write/dangerous statement, the fix isn't "try
    again with the same freedom" — the system prompt already forbids
    it, and blindly retrying wastes an attempt on a failure mode this
    loop isn't designed to negotiate with. Schema-reference errors
    (Phase 8) and real database execution errors ARE retryable: they
    usually stem from a fixable mistake (wrong column name, bad
    syntax, type mismatch) that showing the model the actual error
    can resolve.
    """
    return not any(marker in error for marker in _SECURITY_REJECTION_MARKERS)


def _regenerate_with_correction(
    question: str,
    schema: DatabaseSchema,
    failed_sql: str,
    error_message: str,
) -> GeneratedSQL:
    """
    A second, correction-specific path to the LLM. Deliberately
    separate from LLMSQLGenerator.generate() because the prompt shape
    is different (it includes the failed SQL + error), not just a
    different question.
    """

    client = genai.Client(api_key=settings.gemini_api_key)
    schema_text = schema_to_prompt_text(schema)
    prompt = build_correction_prompt(question, schema_text, failed_sql, error_message)

    response = call_gemini_with_retry(
    client=client,
    model=MODEL_NAME,
    prompt=prompt,
    system_instruction=SYSTEM_INSTRUCTION,
    response_schema=RESPONSE_SCHEMA,
    temperature=0.2,
)
    data = json.loads(response.text)
    return GeneratedSQL(
        sql=data["sql"],
        reasoning_summary=data["reasoning_summary"],
        tables_used=data.get("tables_used", []),
    )


def run_with_correction(
    question: str,
    schema: DatabaseSchema,
    generator: SQLGenerator,
) -> CorrectionLoopResult:
    """
    Runs generate -> validate/execute, retrying with error-informed
    correction up to MAX_CORRECTION_ATTEMPTS times if a retryable
    failure occurs.
    """
    generated = generator.generate(question, schema)
    execution = execute_safe_sql(generated.sql, schema)
    attempts: list[CorrectionAttempt] = []

    attempt_number = 0
    while not execution.success and attempt_number < MAX_CORRECTION_ATTEMPTS:
        attempt_number += 1

        if not _is_retryable(execution.error or ""):
            break  # give up immediately; do not burn an attempt on an unretryable failure

        attempts.append(
            CorrectionAttempt(
                attempt_number=attempt_number,
                failed_sql=generated.sql,
                error=execution.error or "Unknown error",
            )
        )

        generated = _regenerate_with_correction(
            question=question,
            schema=schema,
            failed_sql=generated.sql,
            error_message=execution.error or "Unknown error",
        )
        execution = execute_safe_sql(generated.sql, schema)

    return CorrectionLoopResult(generated=generated, execution=execution, attempts=attempts)