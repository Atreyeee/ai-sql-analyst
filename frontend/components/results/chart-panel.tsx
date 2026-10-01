"use client";

import { motion } from "motion/react";
import type { ChartConfig } from "@/lib/api";
import { toNumber } from "@/lib/utils";

const WIDTH = 640;
const HEIGHT = 280;
const PAD = { top: 16, right: 16, bottom: 36, left: 48 };

/**
 * Renders the backend's Plotly-shaped chart config (Phase 11 of the
 * backend: { chart_type, title, data, layout }) as a lightweight
 * native SVG chart. This stack doesn't include a charting library, so
 * rather than pull one in for three chart types, we draw directly —
 * fewer dependencies, and it lets the reveal animation (bars growing
 * up, line drawing on) be a first-class part of the design rather
 * than a library default.
 */
export function ChartPanel({ chart }: { chart: ChartConfig }) {
  const trace = chart.data[0];
  if (!trace) return null;

  const xLabels = (trace.x ?? []).map((v) => String(v));
  const yValues = (trace.y ?? []).map((v) => toNumber(v) ?? 0);

  if (yValues.length === 0) return null;

  const maxY = Math.max(...yValues, 0);
  const minY = Math.min(...yValues, 0);
  const range = maxY - minY || 1;

  const plotW = WIDTH - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;

  const xScale = (i: number) =>
    PAD.left + (i / Math.max(xLabels.length - 1, 1)) * plotW;
  const yScale = (v: number) =>
    PAD.top + plotH - ((v - minY) / range) * plotH;

  return (
    <div className="border-l-2 border-ink-line px-5 py-5">
      <p className="mb-4 font-mono text-xs uppercase tracking-wide text-ivory-dim">
        {chart.title}
      </p>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        role="img"
        aria-label={chart.title}
      >
        {/* baseline */}
        <line
          x1={PAD.left}
          y1={PAD.top + plotH}
          x2={WIDTH - PAD.right}
          y2={PAD.top + plotH}
          stroke="#242833"
        />

        {chart.chart_type === "bar" && (
          <>
            {yValues.map((v, i) => {
              const barWidth = (plotW / yValues.length) * 0.6;
              const x = xScale(i) - barWidth / 2;
              const y = yScale(Math.max(v, 0));
              const h = Math.abs(yScale(0) - yScale(v));
              return (
                <motion.rect
                  key={i}
                  x={x}
                  width={barWidth}
                  fill="#E2A23B"
                  initial={{ height: 0, y: yScale(0) }}
                  animate={{ height: h, y }}
                  transition={{ duration: 0.6, delay: i * 0.04, ease: "easeOut" }}
                  rx={1}
                />
              );
            })}
          </>
        )}

        {(chart.chart_type === "line" || chart.chart_type === "scatter") && (
          <>
            {chart.chart_type === "line" && (
              <motion.path
                d={`M ${yValues.map((v, i) => `${xScale(i)},${yScale(v)}`).join(" L ")}`}
                fill="none"
                stroke="#E2A23B"
                strokeWidth={2}
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1, ease: "easeOut" }}
              />
            )}
            {yValues.map((v, i) => (
              <motion.circle
                key={i}
                cx={xScale(i)}
                cy={yScale(v)}
                r={3}
                fill="#E2A23B"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3, delay: i * 0.03 }}
              />
            ))}
          </>
        )}

        {/* x-axis labels, thinned if there are many */}
        {xLabels.map((label, i) => {
          const step = Math.max(1, Math.ceil(xLabels.length / 8));
          if (i % step !== 0) return null;
          return (
            <text
              key={i}
              x={xScale(i)}
              y={HEIGHT - 12}
              textAnchor="middle"
              className="fill-ivory-dim"
              fontSize={10}
              fontFamily="var(--font-jbmono)"
            >
              {label.length > 10 ? `${label.slice(0, 9)}…` : label}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
