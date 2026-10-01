"use client";

import { motion } from "motion/react";
import type { AskResponse } from "@/lib/api";
import { SqlBlock } from "@/components/results/sql-block";
import { ResultsTable } from "@/components/results/results-table";
import { ChartPanel } from "@/components/results/chart-panel";
import { ExplanationPanel } from "@/components/results/explanation-panel";
import { CorrectionTrail } from "@/components/results/correction-trail";
import { ErrorPanel } from "@/components/results/error-panel";

const REVEAL = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0 },
};

/**
 * Sections reveal in sequence — SQL, then results, then chart, then
 * explanation — mirroring the order the backend pipeline actually
 * produces them in (Phases 6, 8, 11, 12). This is the "answer
 * arriving like a report being typed out" moment referenced in the
 * hero component; it's the second and last deliberately-orchestrated
 * motion sequence in the app.
 */
export function AnswerSection({ response }: { response: AskResponse }) {
  if (response.error) {
    return (
      <motion.div
        initial="hidden"
        animate="visible"
        variants={REVEAL}
        transition={{ duration: 0.4 }}
        className="mx-auto max-w-3xl space-y-4 px-6 py-16 md:px-12"
      >
        <ErrorPanel message={response.error} />
        {response.sql && <SqlBlock sql={response.sql} />}
        {response.correction_attempts.length > 0 && (
          <CorrectionTrail attempts={response.correction_attempts} />
        )}
      </motion.div>
    );
  }

  const sections = [
    response.sql ? <SqlBlock key="sql" sql={response.sql} /> : null,
    <ResultsTable
      key="table"
      columns={response.columns}
      rows={response.rows}
      truncated={response.truncated}
    />,
    response.chart ? <ChartPanel key="chart" chart={response.chart} /> : null,
    response.explanation ? (
      <ExplanationPanel key="explanation" explanation={response.explanation} />
    ) : null,
    response.correction_attempts.length > 0 ? (
      <CorrectionTrail key="corrections" attempts={response.correction_attempts} />
    ) : null,
  ].filter(Boolean);

  return (
    <div className="mx-auto max-w-3xl px-6 py-16 md:px-12">
      {response.standalone_question &&
        response.standalone_question !== response.question && (
          <p className="mb-6 text-sm text-ivory-dim">
            Understood as: <span className="text-ivory">{response.standalone_question}</span>
          </p>
        )}
      <motion.div
        initial="hidden"
        animate="visible"
        transition={{ staggerChildren: 0.1 }}
        className="space-y-px overflow-hidden bg-ink-line/40"
      >
        {sections.map((section, i) => (
          <motion.div
            key={i}
            variants={REVEAL}
            transition={{ duration: 0.45, ease: "easeOut" }}
            className="bg-ink"
          >
            {section}
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
