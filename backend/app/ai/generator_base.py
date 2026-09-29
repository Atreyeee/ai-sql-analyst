"""
Interface (abstract base class) that every SQL generator must implement.

This is the seam between "orchestration logic" (schema retrieval,
validation, execution, response building) and "how SQL actually gets
produced." Phase 5 implements this with a mock. Phase 6 implements it
with a real LLM. The rest of the pipeline never needs to know which
one it's talking to.
"""

from abc import ABC, abstractmethod

from app.ai.pipeline_models import GeneratedSQL
from app.database.schema_models import DatabaseSchema


class SQLGenerator(ABC):
    @abstractmethod
    def generate(self, question: str, schema: DatabaseSchema) -> GeneratedSQL:
        """
        Given a natural-language question and the database schema,
        return a GeneratedSQL object containing the SQL to execute.

        Implementations must NOT execute the SQL themselves — that
        responsibility belongs to the executor, not the generator.
        """
        raise NotImplementedError