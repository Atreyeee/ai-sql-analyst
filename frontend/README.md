# AI SQL Analyst — Frontend

Next.js (App Router) + TypeScript + Tailwind + GSAP + Motion + Lenis + React Three Fiber.

## What this talks to

This frontend is a pure client for the existing FastAPI backend (Phases 1–16 of
the backend project). It does not reimplement, proxy, or replace any backend
logic — it only calls three endpoints, exactly as they already exist:

| Endpoint | Used for | File |
|---|---|---|
| `GET /health` | Connection-status indicator in the header | `lib/api.ts` → `api.health` |
| `POST /ask` | The core question → SQL → result → chart → explanation flow | `lib/api.ts` → `api.ask` |
| `GET /history` | The query history rail | `lib/api.ts` → `api.history` |

Every field read by a component (`response.sql`, `response.chart`,
`response.explanation.key_findings`, `record.execution_time_ms`, etc.) maps
one-to-one to a field the backend's Pydantic response models already return
(`AskResponse`, `ChartConfig`, `Explanation`, `QueryHistoryRecord` as built
across the backend's phases). No endpoint or field was invented — see the
type definitions and comments in `lib/api.ts` for the full mapping.

The chart is rendered natively in SVG (`components/results/chart-panel.tsx`)
from the backend's Plotly-shaped `{ chart_type, data, layout }` config,
rather than pulling in a charting library — this stack didn't call for one,
and it keeps the chart's reveal animation fully native to the design system.

## Setup

```bash
cd ai-sql-analyst-frontend
npm install
cp .env.local.example .env.local
# edit .env.local if your backend isn't at http://127.0.0.1:8000
npm run dev
```

Requires the backend running separately (`uvicorn app.main:app --reload --port 8000`
from the backend project) with CORS enabled for this frontend's origin — see
the backend's Phase 17 notes for the `CORSMiddleware` snippet
(allow `http://localhost:3000`, Next's default dev port).

Open `http://localhost:3000`.

## Structure

```
app/
  layout.tsx        — fonts (Fraunces/Inter/JetBrains Mono), SmoothScrollProvider
  page.tsx           — orchestrates hero → processing → answer → history against the API
  globals.css         — design tokens, focus states, reduced-motion handling

components/
  providers/           — Lenis smooth scroll
  background/            — the one deliberate 3D element (ambient point field)
  query/                   — hero input, processing state
  results/                  — SQL block, table, chart, explanation, corrections, errors
  history/                   — query history rail
  ui/                          — minimal Button/Textarea primitives

lib/
  api.ts   — typed client + response types mirrored from the backend's actual schemas
  utils.ts  — cn(), numeric-string coercion (Postgres NUMERIC arrives as a JSON string), formatting
```

## Design notes

Palette, type, and layout choices are documented inline at the top of
`tailwind.config.ts` and in comments in `query-hero.tsx` / `answer-section.tsx`.
In short: the query bar is the hero (not a generic headline+illustration),
motion budget is spent on exactly two orchestrated moments (page load, and
the answer revealing section-by-section), and the 3D background is a single
restrained ambient element rather than a centerpiece — all skipped under
`prefers-reduced-motion`.
