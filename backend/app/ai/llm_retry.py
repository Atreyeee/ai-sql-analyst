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

MAX_RETRY_ATTEMPTS = 3


def call_gemini_with_retry(
    client: genai.Client,
    model: str,
    prompt: str,
    system_instruction: str,
    response_schema: dict,
    temperature: float,
):
    """
    Calls Gemini's generate_content with structured output, retrying
    on transient 503 errors with exponential backoff (1s, 2s, 4s).
    Raises the last error if all attempts are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            return client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                ),
            )
        except ServerError as e:
            last_error = e
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(2 ** attempt)
    raise last_error