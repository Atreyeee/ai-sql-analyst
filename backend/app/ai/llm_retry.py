"""
Shared retry-with-backoff wrapper for Gemini API calls.

Multiple call sites (SQL generation, correction, explanation) all
hit the same transient failure mode: Gemini's free tier occasionally
returns 503 UNAVAILABLE under high demand. Rather than duplicating
retry logic in every file that calls the API, this is the single
place that owns the retry policy.
"""

import time

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from app.observability.logger import log_event


MAX_RETRY_ATTEMPTS = 3


def call_gemini_with_retry(
    client: genai.Client,
    model: str,
    prompt: str,
    system_instruction: str,
    response_schema: dict,
    temperature: float,
    request_id: str = "unknown",
):
    """
    Calls Gemini's generate_content with structured output, retrying
    on transient 503 errors with exponential backoff (1s, 2s, 4s).
    Raises the last error if all attempts are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json" if response_schema else None,
                    response_schema=response_schema,
                    temperature=temperature,
                ),
            )
            usage = getattr(response, "usage_metadata", None)
            log_event(
                "llm_call",
                request_id,
                model=model,
                attempt=attempt + 1,
                prompt_tokens=getattr(usage, "prompt_token_count", None),
                completion_tokens=getattr(usage, "candidates_token_count", None),
            )
            return response
        except ServerError as e:
            last_error = e
            log_event("llm_call_retry", request_id, model=model, attempt=attempt + 1, error=str(e))
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(2 ** attempt)
    raise last_error