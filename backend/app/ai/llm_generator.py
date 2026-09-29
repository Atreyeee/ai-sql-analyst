"""
LLM-backed implementation of the SQLGenerator interface, using
Google Gemini's free tier.

This is a drop-in replacement for MockSQLGenerator. The orchestration
code in api/ask.py doesn't need to know or care which implementation
it's using — that's the entire point of the SQLGenerator interface
from Phase 5.
"""

import json

from google import genai
from google.genai import types

from app.ai.generator_base import SQLGenerator
from app.ai.pipeline_models import GeneratedSQL
from app.ai.prompts import SYSTEM_INSTRUCTION, build_user_prompt
from app.database.config import settings
from app.database.inspector import schema_to_prompt_text
from app.database.schema_models import DatabaseSchema

MODEL_NAME = "gemini-2.0-flash"

# JSON schema Gemini is constrained to return. Using response_schema
# (rather than asking for JSON in plain text) means the API itself
# guarantees the response matches this shape — no free-text parsing
# or regex needed on our end.
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "sql": {"type": "STRING"},
        "reasoning_summary": {"type": "STRING"},
        "tables_used": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "confidence": {"type": "NUMBER"},
    },
    "required": ["sql", "reasoning_summary", "tables_used", "confidence"],
}


class LLMSQLGenerator(SQLGenerator):
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def generate(self, question: str, schema: DatabaseSchema) -> GeneratedSQL:
        schema_text = schema_to_prompt_text(schema)
        user_prompt = build_user_prompt(question, schema_text)

        response = self._client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
                temperature=0.1,  # low temperature: we want consistent, literal SQL, not creative variation
            ),
        )

        data = json.loads(response.text)

        return GeneratedSQL(
            sql=data["sql"],
            reasoning_summary=data["reasoning_summary"],
            tables_used=data.get("tables_used", []),
        )