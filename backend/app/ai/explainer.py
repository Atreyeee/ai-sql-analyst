"""
Generates a grounded natural-language explanation of a query result.

The core hallucination-prevention mechanism here is what we DON'T
give the model: raw, uncomputed data to do arithmetic over. Instead
we give it Phase 10's already-verified ResultAnalysis, converted to
readable text, plus a small row sample for color. The model's task
is narrowed to "describe these facts," not "compute and describe."
"""

import json

from google import genai
from google.genai import types
from app.ai.llm_retry import call_gemini_with_retry
from app.ai.pipeline_models import Explanation
from app.ai.prompts import EXPLANATION_SYSTEM_INSTRUCTION, build_explanation_prompt
from app.analytics.result_analysis import ResultAnalysis
from app.database.config import settings

MODEL_NAME = "gemini-3.1-flash-lite"  # keep in sync with llm_generator.py's active model
MAX_SAMPLE_ROWS = 10

EXPLANATION_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "direct_answer": {"type": "STRING"},
        "key_findings": {"type": "ARRAY", "items": {"type": "STRING"}},
        "caveats": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["direct_answer", "key_findings", "caveats"],
}


def _analysis_to_text(analysis: ResultAnalysis) -> str:
    """
    Renders ResultAnalysis as compact, readable text for the prompt —
    same reasoning as schema_to_prompt_text in Phase 3: a plain
    description is easier for the model to use accurately than
    nested JSON.
    """
    lines = [f"Row count: {analysis.row_count}"]
    for col in analysis.column_summaries:
        if col.inferred_type == "numeric":
            lines.append(
                f"- {col.name} (numeric): min={col.min_value}, max={col.max_value}, "
                f"mean={col.mean_value:.2f} if col.mean_value is not None else 'N/A', sum={col.sum_value}"
            )
        elif col.inferred_type == "datetime":
            lines.append(f"- {col.name} (date): range {col.min_date} to {col.max_date}")
        else:
            lines.append(
                f"- {col.name} ({col.inferred_type}): {col.distinct_count} distinct values, "
                f"most common = {col.top_value}"
            )
    for note in analysis.notes:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def _rows_to_text(rows: list[dict], max_rows: int = MAX_SAMPLE_ROWS) -> str:
    sample = rows[:max_rows]
    return json.dumps(sample, default=str, indent=2)


def generate_explanation(
    question: str,
    sql: str,
    rows: list[dict],
    analysis: ResultAnalysis,
) -> Explanation:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

    client = genai.Client(api_key=settings.gemini_api_key)

    analysis_text = _analysis_to_text(analysis)
    row_sample_text = _rows_to_text(rows)
    prompt = build_explanation_prompt(question, sql, analysis_text, row_sample_text)

    response = call_gemini_with_retry(
    client=client,
    model=MODEL_NAME,
    prompt=prompt,
    system_instruction=EXPLANATION_SYSTEM_INSTRUCTION,
    response_schema=EXPLANATION_RESPONSE_SCHEMA,
    temperature=0.2,
)
    data = json.loads(response.text)

    return Explanation(
        direct_answer=data["direct_answer"],
        key_findings=data.get("key_findings", []),
        caveats=data.get("caveats", []),
    )