CREATE TABLE IF NOT EXISTS query_history (
    id                      SERIAL PRIMARY KEY,
    session_id              VARCHAR(64)   NOT NULL,
    question                TEXT          NOT NULL,
    standalone_question     TEXT          NOT NULL,
    sql_generated           TEXT,
    execution_status        VARCHAR(20)   NOT NULL CHECK (execution_status IN ('success', 'failed')),
    execution_time_ms       INTEGER,
    row_count               INTEGER,
    correction_attempt_count INTEGER      NOT NULL DEFAULT 0,
    error_message           TEXT,
    created_at              TIMESTAMP     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_query_history_session ON query_history(session_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created_at ON query_history(created_at);