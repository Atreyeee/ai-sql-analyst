"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { api, ApiError, type AskResponse, type QueryHistoryRecord } from "@/lib/api";
import { QueryHero } from "@/components/query/query-hero";
import { ProcessingState } from "@/components/query/processing-state";
import { AnswerSection } from "@/components/results/answer-section";
import { ErrorPanel } from "@/components/results/error-panel";
import { HistoryRail } from "@/components/history/history-rail";

type DbStatus = "checking" | "connected" | "unreachable";

export default function Home() {
  const [dbStatus, setDbStatus] = useState<DbStatus>("checking");
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [history, setHistory] = useState<QueryHistoryRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const sessionIdRef = useRef<string | null>(null);
  const answerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .health()
      .then(() => setDbStatus("connected"))
      .catch(() => setDbStatus("unreachable"));
    refreshHistory();
  }, []);

  useEffect(() => {
    if (response && answerRef.current) {
      answerRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [response]);

  async function refreshHistory() {
    setHistoryLoading(true);
    try {
      const records = await api.history(15);
      setHistory(records);
    } catch {
      // History is a secondary concern — failing to load it should
      // never block the primary ask flow, mirroring the backend's
      // own stance on history-logging failures (Phase 14).
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleAsk(question: string) {
    setIsLoading(true);
    setRequestError(null);
    setResponse(null);

    try {
      const result = await api.ask({
        question,
        session_id: sessionIdRef.current,
      });
      sessionIdRef.current = result.session_id;
      setResponse(result);
      refreshHistory();
    } catch (err) {
      setRequestError(
        err instanceof ApiError ? err.message : "Something went wrong asking that."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main>
      <header className="fixed top-0 z-20 flex w-full items-center justify-between px-6 py-5 md:px-12">
        <span className="font-display text-sm text-ivory">AI SQL Analyst</span>
        <span
          className={`flex items-center gap-2 font-mono text-xs ${
            dbStatus === "connected"
              ? "text-signal-ok"
              : dbStatus === "unreachable"
                ? "text-signal-error"
                : "text-ivory-dim"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              dbStatus === "connected"
                ? "bg-signal-ok"
                : dbStatus === "unreachable"
                  ? "bg-signal-error"
                  : "animate-pulse-soft bg-ivory-dim"
            }`}
          />
          {dbStatus === "checking"
            ? "connecting"
            : dbStatus === "connected"
              ? "connected"
              : "backend unreachable"}
        </span>
      </header>

      <QueryHero onSubmit={handleAsk} isLoading={isLoading} hasAnswered={!!response} />

      <div ref={answerRef}>
        <AnimatePresence mode="wait">
          {isLoading && (
            <motion.div
              key="processing"
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
            >
              <ProcessingState />
            </motion.div>
          )}

          {!isLoading && requestError && (
            <motion.div
              key="request-error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mx-auto max-w-3xl px-6 py-16 md:px-12"
            >
              <ErrorPanel message={requestError} />
            </motion.div>
          )}

          {!isLoading && !requestError && response && (
            <motion.div
              key="answer"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              <AnswerSection response={response} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <HistoryRail
        records={history}
        isLoading={historyLoading}
        onSelect={(question) => handleAsk(question)}
      />

      <footer className="border-t border-ink-line px-6 py-8 text-xs text-ivory-dim md:px-12">
        Backed by a FastAPI pipeline with schema retrieval, SQL validation, and
        self-correction. Results are computed by Postgres, not estimated by the model.
      </footer>
    </main>
  );
}
