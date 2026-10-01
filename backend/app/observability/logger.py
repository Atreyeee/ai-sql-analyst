"""
Structured logging for the AI pipeline.

Every log call produces a single-line JSON object to stdout, not
free text. This is the standard "12-factor app" approach: the
application doesn't decide where logs go (a file, a log aggregator,
a terminal) — it just writes structured events to stdout, and the
deployment environment routes them wherever they need to go.

Fields are deliberately consistent across every call site so logs
can be filtered/aggregated by field (e.g. "show me every event with
stage=generation and success=false") rather than needing to parse
free text with regex.
"""

import json
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("ai_sql_analyst")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))  # raw JSON, no extra prefix
logger.addHandler(_handler)
logger.propagate = False


def log_event(event: str, request_id: str, **fields: Any) -> None:
    """
    Emits one structured log line. NEVER pass secrets (API keys,
    full prompts containing sensitive data) into fields — this is
    the logging-layer equivalent of Phase 14's "never store
    credentials" rule for query history.
    """
    record = {
        "event": event,
        "request_id": request_id,
        "timestamp": time.time(),
        **fields,
    }
    logger.info(json.dumps(record, default=str))


@contextmanager
def timed_stage(event: str, request_id: str, **extra_fields: Any):
    """
    Context manager that logs a stage's duration automatically,
    whether it succeeds or raises. Usage:

        with timed_stage("retrieval", request_id, retriever="keyword"):
            relevant_schema = retriever.retrieve(question, full_schema)

    This guarantees timing is logged even if the stage raises an
    exception — important because failures are exactly the events
    you most need visibility into.
    """
    start = time.monotonic()
    error: str | None = None
    try:
        yield
    except Exception as e:
        error = str(e)
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)
        log_event(
            event,
            request_id,
            duration_ms=duration_ms,
            success=error is None,
            error=error,
            **extra_fields,
        )