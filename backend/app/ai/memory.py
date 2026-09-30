"""
Bounded, in-memory conversation history and question reformulation.

Design constraint from the project spec: do NOT append unlimited
history to every LLM call. We cap history at MAX_TURNS per session
and only ever send a compact turn summary (question + SQL + answer),
never full row data, into the reformulation prompt.

In-memory storage (a plain dict) is a deliberate simplification for
this phase — it does not survive a server restart and does not scale
across multiple server processes. Phase 14 (query history) will
introduce persistent storage; this phase focuses on the reasoning
pattern, not the storage backend.
"""

import json
import uuid
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from app.database.config import settings
from app.ai.llm_retry import call_gemini_with_retry

MAX_TURNS = 5  # bounded — oldest turns are dropped, not accumulated forever

REFORMULATION_SYSTEM_INSTRUCTION = """You rewrite a follow-up question into a
fully standalone question, using the recent conversation history for context.

Rules:
- If the new question is already standalone (doesn't depend on prior context), return it unchanged.
- Only use information present in the conversation history — do not invent context.
- Keep the rewritten question concise and natural.
- Respond with ONLY the rewritten question text, nothing else.
"""


@dataclass
class Turn:
    question: str
    standalone_question: str
    sql: str
    direct_answer: str


@dataclass
class SessionHistory:
    turns: list[Turn] = field(default_factory=list)

    def add(self, turn: Turn) -> None:
        self.turns.append(turn)
        if len(self.turns) > MAX_TURNS:
            self.turns = self.turns[-MAX_TURNS:]  # keep only the most recent N

    def as_text(self) -> str:
        lines = []
        for i, t in enumerate(self.turns, start=1):
            lines.append(f"Turn {i}: Q: \"{t.standalone_question}\" -> Answer: {t.direct_answer}")
        return "\n".join(lines)


# In-memory session store: session_id -> SessionHistory.
# A dict is fine for a single-process dev server; a real deployment
# would use Redis or a DB-backed store keyed by session_id instead.
_sessions: dict[str, SessionHistory] = {}


def get_or_create_session(session_id: str | None) -> tuple[str, SessionHistory]:
    if session_id is None or session_id not in _sessions:
        new_id = session_id or str(uuid.uuid4())
        _sessions[new_id] = SessionHistory()
        return new_id, _sessions[new_id]
    return session_id, _sessions[session_id]


def reformulate_question(question: str, history: SessionHistory) -> str:
    """
    Rewrites a possibly-context-dependent question into a standalone
    one, using bounded recent history. If there's no history yet,
    skips the LLM call entirely — nothing to reformulate against.
    """
    if not history.turns:
        return question

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"""Conversation history:
{history.as_text()}

New question: "{question}"

Rewrite the new question as a standalone question, following the rules in the system instruction.
"""

    response = call_gemini_with_retry(
        client=client,
        model=settings.gemini_model,
        prompt=prompt,
        system_instruction=REFORMULATION_SYSTEM_INSTRUCTION,
        response_schema=None,  # plain text response, not structured JSON
        temperature=0.0,
    )
    return response.text.strip()