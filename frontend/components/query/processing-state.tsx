"use client";

import { motion, AnimatePresence } from "motion/react";
import { useEffect, useState } from "react";

const STAGES = [
  "Reading your question",
  "Finding the relevant tables",
  "Writing SQL",
  "Running the query",
  "Preparing the explanation",
];

/**
 * A staged, editorial processing indicator rather than a generic
 * spinner. The stages are illustrative (the frontend has no real-time
 * signal for which backend phase is active) but rotate at a pace that
 * reads as "working through a real pipeline," which is true to what's
 * actually happening server-side across Phases 5-12 of the backend.
 */
export function ProcessingState() {
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, 1400);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="mx-auto flex max-w-3xl flex-col items-start gap-4 px-6 py-20 md:px-12"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber" />
        </span>
        <span className="font-mono text-xs uppercase tracking-wide text-ivory-dim">
          Analyzing
        </span>
      </div>

      <AnimatePresence mode="wait">
        <motion.p
          key={stageIndex}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="font-display text-2xl text-ivory md:text-3xl"
        >
          {STAGES[stageIndex]}…
        </motion.p>
      </AnimatePresence>

      <div className="mt-2 h-px w-full max-w-sm overflow-hidden bg-ink-line">
        <motion.div
          className="h-full bg-amber"
          initial={{ width: "0%" }}
          animate={{ width: `${((stageIndex + 1) / STAGES.length) * 100}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}
