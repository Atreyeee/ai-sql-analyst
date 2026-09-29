-- ============================================================
-- Read-only role for the application's query executor.
-- This is the last line of defense: even if application-level
-- SQL validation is bypassed, Postgres itself will reject any
-- write attempt at the permissions level.
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ai_sql_readonly') THEN
        CREATE ROLE ai_sql_readonly WITH LOGIN PASSWORD 'readonly_pw_change_me';
    END IF;
END
$$;

-- Allow connecting to the database and using the schema
GRANT CONNECT ON DATABASE ai_sql_analyst TO ai_sql_readonly;
GRANT USAGE ON SCHEMA public TO ai_sql_readonly;

-- Grant SELECT only — no INSERT/UPDATE/DELETE/DDL of any kind
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ai_sql_readonly;

-- Ensure any tables created in the future are also read-only for this role
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO ai_sql_readonly;

-- Also cap how long any single query from this role can run
ALTER ROLE ai_sql_readonly SET statement_timeout = '5s';