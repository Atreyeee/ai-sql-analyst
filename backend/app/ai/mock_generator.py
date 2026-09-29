"""
A fake SQL generator used to validate the pipeline architecture
before introducing a real LLM.

It uses simple keyword matching against the question to pick one of
a few hand-written SQL templates. This is deliberately dumb — the
goal isn't to build a good text-to-SQL system here, it's to prove
that question -> SQL -> validation -> execution -> response works
end-to-end with ZERO dependency on an external API.
"""

from app.ai.generator_base import SQLGenerator
from app.ai.pipeline_models import GeneratedSQL
from app.database.schema_models import DatabaseSchema


class MockSQLGenerator(SQLGenerator):
    def generate(self, question: str, schema: DatabaseSchema) -> GeneratedSQL:
        q = question.lower()

        if "top" in q and "product" in q and "revenue" in q:
            return GeneratedSQL(
                sql=(
                    "SELECT p.product_name, "
                    "SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)) AS revenue "
                    "FROM order_items oi "
                    "JOIN products p ON oi.product_id = p.product_id "
                    "GROUP BY p.product_name "
                    "ORDER BY revenue DESC "
                    "LIMIT 5"
                ),
                reasoning_summary="Matched a 'top products by revenue' pattern.",
                tables_used=["order_items", "products"],
            )

        if "customer" in q and ("count" in q or "how many" in q):
            return GeneratedSQL(
                sql="SELECT COUNT(*) AS customer_count FROM customers",
                reasoning_summary="Matched a 'customer count' pattern.",
                tables_used=["customers"],
            )

        if "order" in q and ("status" in q or "how many" in q):
            return GeneratedSQL(
                sql=(
                    "SELECT status, COUNT(*) AS order_count "
                    "FROM orders GROUP BY status ORDER BY order_count DESC"
                ),
                reasoning_summary="Matched an 'orders by status' pattern.",
                tables_used=["orders"],
            )

        # Deliberate fallback: an intentionally invalid table name.
        # This lets us test what happens when SQL execution fails
        # further down the pipeline (Phase 9 will build on this).
        return GeneratedSQL(
            sql="SELECT * FROM unknown_table_for_testing",
            reasoning_summary="No pattern matched; returning a deliberately invalid query.",
            tables_used=[],
        )