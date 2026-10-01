import type { Explanation } from "@/lib/api";

export function ExplanationPanel({ explanation }: { explanation: Explanation }) {
  return (
    <div className="border-l-2 border-amber/40 px-5 py-6">
      <p className="mb-2 font-mono text-xs uppercase tracking-wide text-ivory-dim">
        AI analysis
      </p>
      <p className="max-w-measure font-display text-2xl leading-snug text-ivory md:text-[1.75rem]">
        {explanation.direct_answer}
      </p>

      {explanation.key_findings.length > 0 && (
        <ul className="mt-6 max-w-measure space-y-2.5">
          {explanation.key_findings.map((finding, i) => (
            <li key={i} className="flex gap-3 text-[15px] leading-relaxed text-ivory/90">
              <span className="mt-2 h-1 w-1 flex-shrink-0 rounded-full bg-amber" />
              {finding}
            </li>
          ))}
        </ul>
      )}

      {explanation.caveats.length > 0 && (
        <div className="mt-6 max-w-measure border-t border-ink-line pt-4">
          {explanation.caveats.map((caveat, i) => (
            <p key={i} className="text-sm text-ivory-dim">
              {caveat}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
