/**
 * Typed client for the existing FastAPI backend.
 *
 * These types mirror the backend's actual Pydantic response models
 * (app/ai/pipeline_models.py, app/analytics/result_analysis.py,
 * app/analytics/visualization.py, app/database/history_repository.py)
 * as built across the backend project's phases. Nothing here is
 * invented — every field maps to a field the backend genuinely
 * returns. If the backend adds/renames a field, this file is the
 * one place to update it; every component consumes these types,
 * never a raw fetch response.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

// ---- /health ----------------------------------------------------

export interface HealthResponse {
  status: string;
  service: string;
}

// ---- /ask ---------------------------------------------------------

export interface AskRequest {
  question: string;
  session_id?: string | null;
}

export interface CorrectionAttempt {
  attempt_number: number;
  failed_sql: string;
  error: string;
}

export interface ColumnSummary {
  name: string;
  inferred_type: "numeric" | "datetime" | "categorical" | "text";
  null_count: number;
  min_value: number | null;
  max_value: number | null;
  mean_value: number | null;
  sum_value: number | null;
  min_date: string | null;
  max_date: string | null;
  distinct_count: number | null;
  top_value: string | null;
}

export interface ResultAnalysis {
  row_count: number;
  column_summaries: ColumnSummary[];
  notes: string[];
}

export type ChartType = "line" | "bar" | "scatter";

export interface ChartTrace {
  type: string;
  x?: Array<string | number | null>;
  y?: Array<string | number | null>;
  mode?: string;
  name?: string;
}

export interface ChartConfig {
  chart_type: ChartType;
  title: string;
  data: ChartTrace[];
  layout: Record<string, unknown>;
}

export interface Explanation {
  direct_answer: string;
  key_findings: string[];
  caveats: string[];
}

export interface AskResponse {
  session_id: string;
  question: string;
  standalone_question: string | null;
  sql: string | null;
  reasoning_summary: string | null;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  truncated: boolean;
  error: string | null;
  correction_attempts: CorrectionAttempt[];
  analysis: ResultAnalysis | null;
  chart: ChartConfig | null;
  explanation: Explanation | null;
}

// ---- /history -------------------------------------------------------

export interface QueryHistoryRecord {
  id: number | null;
  session_id: string;
  question: string;
  standalone_question: string;
  sql_generated: string | null;
  execution_status: "success" | "failed";
  execution_time_ms: number | null;
  row_count: number | null;
  correction_attempt_count: number;
  error_message: string | null;
  created_at: string | null;
}

// ---- client ----------------------------------------------------------

class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(
      "Could not reach the backend. Confirm the FastAPI server is running."
    );
  }

  if (!res.ok) {
    throw new ApiError(`Request failed (${res.status})`, res.status);
  }

  return (await res.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  ask: (body: AskRequest) =>
    request<AskResponse>("/ask", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  history: (limit = 15) =>
    request<QueryHistoryRecord[]>(`/history?limit=${limit}`),
};

export { ApiError };
