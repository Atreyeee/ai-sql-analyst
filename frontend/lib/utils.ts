import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formats a table cell value for display.
 *
 * Postgres NUMERIC/DECIMAL columns arrive over JSON as quoted strings
 * (psycopg2/SQLAlchemy serialize Decimal this way), not native numbers.
 * Rather than trusting the JSON type, we detect numeric-looking strings
 * and format them properly — the same defensive stance the project's
 * vanilla-JS frontend took in an earlier phase, ported here.
 */
export function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (typeof value === "string" && value.trim() !== "") {
    const asNumber = Number(value);
    if (!Number.isNaN(asNumber)) {
      return asNumber.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
  }
  return String(value);
}

export function toNumber(value: unknown): number | null {
  if (typeof value === "number") return value;
  if (typeof value === "string" && value.trim() !== "") {
    const n = Number(value);
    return Number.isNaN(n) ? null : n;
  }
  return null;
}

export function formatMs(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
