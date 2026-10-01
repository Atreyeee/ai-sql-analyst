"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function SqlBlock({ sql }: { sql: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="border-l-2 border-amber/40 bg-ink-panel">
      <div className="flex items-center justify-between border-b border-ink-line px-5 py-2.5">
        <span className="font-mono text-xs uppercase tracking-wide text-ivory-dim">
          Generated SQL
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-ivory-dim transition-colors hover:text-ivory"
          aria-label="Copy SQL to clipboard"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy
            </>
          )}
        </button>
      </div>
      <pre className="hairline-scroll overflow-x-auto px-5 py-4 font-mono text-sm leading-relaxed text-ivory">
        <code>{sql}</code>
      </pre>
    </div>
  );
}
