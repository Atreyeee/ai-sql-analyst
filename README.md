# AI SQL Analyst

A natural-language interface for querying a relational database. Ask a question in plain English, and the system retrieves the relevant schema, generates SQL with an LLM, validates and safely executes it, analyzes the result, decides whether a chart adds value, and explains the answer in grounded, factual language — all with multiple layers of safety between the model and the database.

---

## Table of contents

- [Problem statement](#problem-statement)
- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [AI pipeline](#ai-pipeline)
- [Database schema](#database-schema)
- [Security approach](#security-approach)
- [Evaluation methodology](#evaluation-methodology)
- [API documentation](#api-documentation)
- [Local setup](#local-setup)
- [Docker setup](#docker-setup)
- [Environment variables](#environment-variables)
- [Example queries](#example-queries)
- [Results](#results)
- [Limitations](#limitations)
- [Future improvements](#future-improvements)

---

## Problem statement

Business users who need data answers are usually blocked on a data analyst or engineer who knows SQL. Text-to-SQL tools exist, but most either (a) trust LLM-generated SQL to run directly against production data with no safety layer, or (b) stop at "generate SQL" without analyzing, visualizing, or explaining the result. This project builds the fuller pipeline: a question doesn't just become SQL — it becomes a validated, safely-executed query, a statistically-analyzed result, an appropriate visualization, and a grounded explanation, with the LLM never trusted blindly at any step.

## Features

- Natural-language question answering over a PostgreSQL e-commerce database
- Schema-aware SQL generation (not a hardcoded schema in the prompt)
- Multi-layer SQL safety validation: statement-type restriction, multi-statement rejection, dangerous-function blocking, and a database-level read-only role as a final backstop
- Parser-based schema-reference validation (catches hallucinated tables/columns before execution)
- Bounded, error-aware SQL self-correction (up to 2 retries, with security rejections explicitly excluded from retry)
- Two schema-retrieval strategies (keyword matching and embedding-based semantic retrieval) so only relevant tables are sent to the LLM
- Automatic statistical result analysis (Pandas-based column typing, nulls, summary stats)
- Rule-based chart-type selection (line / bar / scatter, or no chart when one wouldn't add value) with Plotly-compatible config output
- Grounded natural-language explanation that is not permitted to invent numbers
- Bounded conversation memory for follow-up questions ("What about just 2025?")
- Persistent query history with execution metadata
- Structured, trace-able observability (every pipeline stage logged with a shared request ID)
- A benchmark evaluation framework measuring execution success, result correctness, correction rate, and latency
- A premium, animated Next.js/TypeScript frontend

## Architecture

```
User
 |
 v
Frontend (Next.js / React / TypeScript)
 |
 v
FastAPI
 |
 v
Conversation Reformulation  (resolves follow-up questions into standalone ones)
 |
 v
Schema Retrieval  (keyword or embedding-based — only relevant tables selected)
 |
 v
LLM  (Gemini, structured JSON output)
 |
 v
SQL Generation
 |
 v
SQL Validation  (security layer + schema-reference layer)
 |
 v
Safe SQL Executor  (read-only database role, statement timeout, row cap)
 |
 v
PostgreSQL  <---- on failure: bounded self-correction loop feeds the error back to the LLM
 |
 v
Result
 |--- Statistical Analysis (Pandas)
 |--- Visualization decision + config (rule-based)
 |--- Natural Language Explanation (grounded in the computed analysis, not re-derived)
 |
 v
Frontend (SQL, table, chart, explanation, history)
```

Every stage is logged with a shared `request_id`, so a single request's full path through the system can be reconstructed from structured logs.

## Tech stack

| Layer | Technology |
|---|---|
| Backend framework | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL |
| LLM | Google Gemini API (structured JSON output via `response_schema`) |
| Data processing | Pandas, NumPy |
| SQL parsing | sqlglot |
| Visualization (backend) | Rule-based chart-type selection, Plotly-compatible JSON config |
| Frontend | Next.js (App Router), React, TypeScript, Tailwind CSS |
| Frontend animation | GSAP, Motion, Lenis (smooth scroll), React Three Fiber (ambient background only) |
| Containerization | Docker, Docker Compose |
| Version control | Git / GitHub |

LangChain, LlamaIndex, and dedicated vector databases (Pinecone, Chroma) were deliberately not used — the text-to-SQL pipeline, schema retrieval, and correction loop are hand-built so the underlying mechanics are fully understood rather than hidden behind a framework.

## AI pipeline

| Stage | What it does | Key design decision |
|---|---|---|
| Reformulation | Rewrites a follow-up question into a standalone one using bounded recent history | History capped at 5 turns; never sent unbounded |
| Schema retrieval | Selects only the tables relevant to the question | Keyword matching (fast, free) and embedding-based semantic matching (handles vocabulary mismatches like "clients" vs "customers"); both expand selections via foreign keys so joins stay possible |
| SQL generation | Produces SQL from the question + retrieved schema | Structured output via Gemini's `response_schema`, not free-text JSON parsing; low temperature (0.1) for literalness |
| Validation | Rejects unsafe or schema-invalid SQL before execution | Two independent layers: security (statement type, keyword blocklist, dangerous functions) and schema-reference correctness (parser-based, via sqlglot) |
| Execution | Runs the SQL | Read-only database role, statement timeout, row cap, always returns a structured result rather than raising |
| Self-correction | Retries a failed query with the actual error fed back to the model | Bounded at 2 attempts; security rejections are explicitly excluded from retry |
| Result analysis | Computes statistics in code, not via the LLM | Pandas-based column typing (numeric / datetime / categorical / text), nulls, summary stats |
| Visualization | Decides whether and how to chart the result | Deterministic rule-based decision tree, not an LLM call |
| Explanation | Describes the result in plain language | Grounded in the pre-computed analysis; the model is instructed not to invent or recompute numbers |

## Database schema

```
customers ----< orders ----< order_items >---- products >---- categories
                  |
                  1
                  |
               payments
```

| Table | Purpose |
|---|---|
| `customers` | Customer identity and location |
| `categories` | Product categories |
| `products` | Product catalog, priced per unit |
| `orders` | One row per order, with status |
| `order_items` | Line items per order (quantity, unit price, discount) |
| `payments` | One payment per order, with method and status |

`query_history` is a separate, application-owned table (not part of the e-commerce domain) that logs every question asked, its SQL, execution status, timing, and correction count.

## Security approach

| Layer | Mechanism |
|---|---|
| Statement restriction | Only `SELECT` / `WITH` statements are permitted; everything else (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, and others) is rejected |
| Multi-statement protection | SQL is parsed (not naively split on `;`) to reject stacked statements while tolerating semicolons inside string literals |
| Keyword and function blocklist | Forbidden keywords are checked anywhere in the parsed statement, including inside CTEs and subqueries; dangerous functions (`pg_sleep`, `pg_read_file`, `dblink`, and others) are blocked separately |
| Schema-reference validation | A parsed AST (via sqlglot) is checked against the actual schema shown to the model; hallucinated tables or columns are rejected before reaching the database |
| Database-level backstop | All AI-generated SQL executes under a dedicated Postgres role with `SELECT`-only privileges, independent of application-level validation |
| Timeouts and limits | Statement timeout enforced at both the connection and database-role level; results capped at 1,000 rows |
| Credential handling | All credentials and API keys are loaded from environment variables; nothing is hardcoded or logged |
| Query history | Logs questions, SQL, and execution metadata only — never credentials or secrets |

The database role restriction is treated as the ultimate backstop: even if every application-level validation layer had a bug, the database itself refuses to execute a write under that role.

## Evaluation methodology

SQL correctness is evaluated on **result properties**, not exact SQL string matching — two different SQL queries can produce the same correct answer, and the same question can legitimately produce slightly different SQL across runs due to LLM non-determinism. Each benchmark question defines expected result characteristics (row count ranges, expected columns by hint, positive-value checks) rather than an exact expected query or exact expected output.

Metrics tracked per run:

- SQL execution success rate (did the query run without error)
- Result correctness rate (did the result satisfy the question's expected properties)
- Correction rate (fraction of questions that required at least one self-correction attempt)
- Average and P95 latency
- Accuracy broken down by SQL pattern category (simple select, filtering, aggregation, joins, subqueries, CTEs, window functions, date operations, ranking, multi-condition)

## API documentation

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/schema` | Structured introspected database schema |
| GET | `/schema/prompt-text` | Schema rendered as LLM-prompt-ready text |
| POST | `/schema/retrieval-debug` | Shows which tables a retriever would select for a given question |
| POST | `/query/raw` | Runs arbitrary SQL through validation and the safe executor (development/testing use) |
| POST | `/ask` | The primary endpoint: question in, full answer (SQL, results, chart, explanation) out |
| GET | `/history` | Recent query history |
| GET | `/history/{id}` | A single history record |

**`POST /ask` request:**

```json
{
  "question": "What were the top 5 products by revenue?",
  "session_id": null
}
```

**`POST /ask` response (success):**

```json
{
  "session_id": "uuid",
  "question": "What were the top 5 products by revenue?",
  "standalone_question": "What were the top 5 products by revenue?",
  "sql": "SELECT ...",
  "reasoning_summary": "...",
  "columns": ["product_name", "revenue"],
  "rows": [ { "product_name": "...", "revenue": "..." } ],
  "row_count": 5,
  "truncated": false,
  "error": null,
  "correction_attempts": [],
  "analysis": { "row_count": 5, "column_summaries": [ /* ... */ ], "notes": [ /* ... */ ] },
  "chart": { "chart_type": "bar", "title": "...", "data": [ /* ... */ ], "layout": { /* ... */ } },
  "explanation": {
    "direct_answer": "...",
    "key_findings": [ "..." ],
    "caveats": [ ]
  }
}
```

Interactive documentation (auto-generated from the Pydantic models) is available at `/docs` while the backend is running.

## Local setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ai-sql-analyst

# 2. Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY and database URLs

# 3. Database (see Docker setup below for the containerized alternative)
# Create the database, then:
psql "<DATABASE_URL>" -f ../data/ecommerce/schema.sql
psql "<DATABASE_URL>" -f ../data/ecommerce/create_readonly_user.sql
psql "<DATABASE_URL>" -f ../data/ecommerce/query_history_schema.sql
python ../data/ecommerce/seed.py

# 4. Run the backend
uvicorn app.main:app --reload --port 8000

# 5. Frontend (separate terminal)
cd ../frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Docker setup

```bash
docker compose up --build
```

This builds the backend image and starts PostgreSQL with the schema, read-only role, and query history table created automatically on first boot (via Postgres's standard `docker-entrypoint-initdb.d` mechanism). Synthetic e-commerce data still needs to be seeded once against the running container:

```bash
DATABASE_URL="postgresql://user:password@localhost:5432/ai_sql_analyst" python data/ecommerce/seed.py
```

To stop:

```bash
docker compose down        # keeps data (named volume persists)
docker compose down -v     # wipes data — required to re-trigger the init scripts
```

The frontend is run separately (`npm run dev`), not containerized in this setup — see [Future improvements](#future-improvements).

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | Backend | Main (read/write) database connection, used for schema introspection and query history |
| `READONLY_DATABASE_URL` | Backend | Restricted connection used exclusively to execute AI-generated SQL |
| `GEMINI_API_KEY` | Backend | Google Gemini API key |
| `GEMINI_MODEL` | Backend | Active Gemini model name, centralized so a provider-side model deprecation is a one-line config change |
| `APP_ENV` | Backend | `development` / `test` / `production` — `test` swaps in the mock SQL generator so the test suite never calls the real LLM |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | URL of the running FastAPI backend |

Real values live only in untracked `.env` / `.env.local` files; `.env.example` / `.env.local.example` document the required keys without real values.

## Example queries

| Question | SQL pattern exercised |
|---|---|
| "How many customers do we have?" | Simple aggregation |
| "How many orders are in each status?" | Group by |
| "What were the top 5 products by revenue?" | Join, aggregation, ranking |
| "What was total revenue by month in 2024?" | Date truncation, time series |
| "Which customers have spent more than the average customer spend?" | Subquery |
| "Rank products by total revenue, showing their rank alongside the revenue" | Window function |
| "What about only in 2025?" (as a follow-up) | Conversation reformulation |

## Results

The figures below are from an actual evaluation run against a 12-question benchmark subset (not the full planned 30-50 question set) and are reported as measured, not estimated.

| Metric | Value |
|---|---|
| SQL execution success rate | 75.0% |
| Result correctness rate | 75.0% |
| Correction rate | 33.3% |
| Average latency | 7.87s |
| P95 latency | 21.8s |

By category (n=1 per category in this subset — directional, not statistically robust):

| Category | Accuracy |
|---|---|
| Simple select | 100% |
| Filtering | 100% |
| Aggregation | 100% |
| Group by | 100% |
| Joins | 100% |
| Subqueries | 0% |
| CTEs | 0% |
| Window functions | 0% |
| Date operations | 100% |
| Ranking | 100% |
| Multi-condition | 100% |
| Edge case (empty result) | 100% |

The pattern is consistent and explainable rather than random: every failure occurred on the three most structurally complex SQL categories (subqueries, CTEs, window functions), and every failure exhausted the full self-correction budget (2/2 attempts) without succeeding. Simpler patterns — including joins, aggregation, and ranking — were 100% correct in this run.

## Limitations

- The evaluation benchmark currently covers 12 of the planned 30-50 questions; category-level accuracy above is directional, not statistically robust.
- The schema-reference validator (Phase 8) does not resolve SELECT-list aliases, so a query referencing its own `AS` alias in `GROUP BY` or `ORDER BY` can be incorrectly rejected as an "unknown column" — the self-correction loop typically compensates by having the model rewrite the alias as its full expression, at the cost of one extra LLM round trip.
- Chart-type selection currently defaults to bar charts for all category + numeric shapes, including genuine part-to-whole questions; true pie/donut rendering was scoped out in favor of bar charts, which are generally easier to read accurately.
- Conversation memory is stored in-process, in memory; it does not survive a server restart and would not work correctly across multiple server processes behind a load balancer.
- The categorical-vs-text column classification heuristic (distinct count and distinct ratio) is a heuristic, not a rigorous statistical test, and can misclassify edge cases at specific row-count/cardinality combinations.
- The LLM provider's available model names have changed multiple times during this project's development (model deprecations and new releases), which is itself documented as a real, encountered production concern rather than a one-time setup detail.
- Docker Compose containerizes the backend and database; the frontend currently runs outside the container setup.
- The backend's retry-with-backoff logic for transient LLM provider errors (503s) is applied per call site rather than fully centralized.

## Future improvements

- Extend the evaluation benchmark to the full 30-50 question set across all required SQL categories
- Resolve SELECT-list aliases in the schema validator to remove the false-positive rejection noted above
- Move conversation session storage to a shared backing store (Redis or database-backed) so it survives restarts and works across multiple server processes
- Containerize the frontend for full `docker compose up` parity
- Add a frontend container and deploy both services together
- Expand chart-type selection to support part-to-whole visualizations as an explicit, opt-in case
- Add OpenTelemetry-based distributed tracing, building on the existing `request_id` threading
- Deploy to Azure with managed Postgres and secrets handled via a managed secrets store rather than `.env` files