import type { CorrectionAttempt } from "@/lib/api";

/**
 * Shown only when the backend's self-correction loop (Phase 9) fired.
 * Surfacing this rather than hiding it behind a "clean" final answer
 * is a deliberate transparency choice — it mirrors the backend's own
 * decision to always return correction_attempts rather than discard them.
 */
export function CorrectionTrail({ attempts }: { attempts: CorrectionAttempt[] }) {
  if (attempts.length === 0) return null;

  return (
    <details className="border-l-2 border-ink-line px-5 py-4">
      <summary className="cursor-pointer font-mono text-xs uppercase tracking-wide text-ivory-dim">
        Self-corrected after {attempts.length} attempt{attempts.length > 1 ? "s" : ""}
      </summary>
      <ol className="mt-4 space-y-4">
        {attempts.map((a) => (
          <li key={a.attempt_number} className="text-sm">
            <p className="mb-1 text-ivory-dim">Attempt {a.attempt_number}</p>
            <pre className="hairline-scroll overflow-x-auto bg-ink-panel px-3 py-2 font-mono text-xs text-ivory/80">
              {a.failed_sql}
            </pre>
            <p className="mt-1 text-xs text-signal-error">{a.error}</p>
          </li>
        ))}
      </ol>
    </details>
  );
}
