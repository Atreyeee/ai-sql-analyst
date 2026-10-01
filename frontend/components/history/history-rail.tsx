"use client";

import { motion } from "motion/react";
import type { QueryHistoryRecord } from "@/lib/api";
import { formatMs } from "@/lib/utils";

interface HistoryRailProps {
  records: QueryHistoryRecord[];
  onSelect: (question: string) => void;
  isLoading: boolean;
}

export function HistoryRail({ records, onSelect, isLoading }: HistoryRailProps) {
  return (
    <section className="mx-auto max-w-3xl px-6 py-20 md:px-12">
      <p className="mb-8 font-mono text-xs uppercase tracking-wide text-ivory-dim">
        Query history
      </p>

      {isLoading && records.length === 0 && (
        <p className="text-sm text-ivory-dim">Loading history…</p>
      )}

      {!isLoading && records.length === 0 && (
        <div className="border-l-2 border-ink-line py-8 pl-5">
          <p className="font-display text-xl text-ivory">Nothing asked yet.</p>
          <p className="mt-2 max-w-measure text-sm text-ivory-dim">
            Every question you ask will appear here, so you can revisit or rerun it later.
          </p>
        </div>
      )}

      <ol className="relative border-l border-ink-line">
        {records.map((r, i) => (
          <motion.li
            key={r.id ?? i}
            initial={{ opacity: 0, x: -6 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.35, delay: Math.min(i, 8) * 0.03 }}
          >
            <button
              onClick={() => onSelect(r.question)}
              className="group -ml-px flex w-full items-start gap-4 border-l border-transparent py-3 pl-5 text-left transition-colors hover:border-amber"
            >
              <span
                className={`mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                  r.execution_status === "success" ? "bg-signal-ok" : "bg-signal-error"
                }`}
                aria-hidden="true"
              />
              <span className="flex-1">
                <span className="block text-sm text-ivory transition-colors group-hover:text-amber">
                  {r.question}
                </span>
                <span className="mt-0.5 block text-xs text-ivory-dim">
                  {formatMs(r.execution_time_ms)}
                  {r.row_count !== null ? ` · ${r.row_count} rows` : ""}
                  {r.correction_attempt_count > 0
                    ? ` · ${r.correction_attempt_count} correction${r.correction_attempt_count > 1 ? "s" : ""}`
                    : ""}
                </span>
              </span>
            </button>
          </motion.li>
        ))}
      </ol>
    </section>
  );
}
