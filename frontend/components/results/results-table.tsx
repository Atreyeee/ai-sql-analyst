"use client";

import { formatCellValue } from "@/lib/utils";

interface ResultsTableProps {
  columns: string[];
  rows: Record<string, unknown>[];
  truncated: boolean;
}

const RENDER_CAP = 100; // protects the DOM even though the API already caps at 1000 rows

export function ResultsTable({ columns, rows, truncated }: ResultsTableProps) {
  if (rows.length === 0) {
    return (
      <div className="border-l-2 border-ink-line px-5 py-10 text-center">
        <p className="font-display text-xl text-ivory">No rows returned.</p>
        <p className="mt-2 text-sm text-ivory-dim">
          The query ran successfully but found nothing matching your question.
        </p>
      </div>
    );
  }

  const visibleRows = rows.slice(0, RENDER_CAP);

  return (
    <div>
      <div className="hairline-scroll overflow-x-auto">
        <table className="w-full min-w-[480px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-ink-line text-left">
              {columns.map((col) => (
                <th
                  key={col}
                  scope="col"
                  className="whitespace-nowrap px-4 py-3 font-mono text-xs uppercase tracking-wide text-ivory-dim"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-ink-line/60 transition-colors hover:bg-ink-panel/60"
              >
                {columns.map((col) => (
                  <td key={col} className="whitespace-nowrap px-4 py-2.5 font-mono text-ivory">
                    {formatCellValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(truncated || rows.length > RENDER_CAP) && (
        <p className="px-4 py-3 text-xs text-ivory-dim">
          {truncated
            ? "Result was truncated by the backend at 1,000 rows."
            : `Showing the first ${RENDER_CAP} of ${rows.length} rows.`}
        </p>
      )}
    </div>
  );
}
