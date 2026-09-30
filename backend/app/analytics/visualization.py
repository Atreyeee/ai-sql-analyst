"""
Automatic chart-type selection and Plotly-compatible config generation.

Chart selection is a deterministic decision tree based on the column
types computed in Phase 10 (ResultAnalysis) — not an LLM call. This
keeps visualization fast, predictable, and easy to reason about.

The backend never renders an image. It returns a JSON structure
matching Plotly.js's `data` + `layout` format, which the frontend
(Phase 17) passes directly to Plotly.newPlot().
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.analytics.result_analysis import ColumnSummary, ResultAnalysis

MAX_CATEGORIES_FOR_BAR = 15
MAX_CATEGORIES_FOR_PIE = 8
TOP_N_WHEN_TOO_MANY_CATEGORIES = 10


class ChartType(str, Enum):
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    PIE = "pie"


class ChartConfig(BaseModel):
    chart_type: ChartType
    title: str
    data: list[dict[str, Any]]   # Plotly "data" array (traces)
    layout: dict[str, Any]        # Plotly "layout" object


def _find_columns_by_type(summaries: list[ColumnSummary], inferred_type: str) -> list[ColumnSummary]:
    return [s for s in summaries if s.inferred_type == inferred_type]


def decide_chart_type(analysis: ResultAnalysis) -> ChartType | None:
    """
    Pure decision function: given the statistical shape of a result,
    decide whether a chart adds value and, if so, which type.
    Returns None when no chart should be shown — this is a valid,
    expected outcome, not a failure case.
    """
    if analysis.row_count == 0:
        return None

    numeric_cols = _find_columns_by_type(analysis.column_summaries, "numeric")
    datetime_cols = _find_columns_by_type(analysis.column_summaries, "datetime")
    categorical_cols = _find_columns_by_type(analysis.column_summaries, "categorical")

    # Single row: a chart doesn't add value over just showing the number(s).
    if analysis.row_count == 1:
        return None

    # Time series: one datetime axis + at least one numeric measure.
    if datetime_cols and numeric_cols:
        return ChartType.LINE

    # Category + numeric: the most common analytical shape.
    if categorical_cols and numeric_cols:
        category_col = categorical_cols[0]
        distinct = category_col.distinct_count or 0
        if distinct <= MAX_CATEGORIES_FOR_PIE and len(categorical_cols) == 1 and len(numeric_cols) == 1:
            # Only pick pie for a SIMPLE two-column part-to-whole shape.
            # More columns present usually means the user wants more
            # detail than a pie can show — bar handles that better.
            pass  # we default to bar below; pie is opt-in, see note.
        return ChartType.BAR

    # Two numeric columns, no category/time axis: relationship between
    # two measures is what scatter is for.
    if len(numeric_cols) == 2 and not categorical_cols and not datetime_cols:
        return ChartType.SCATTER

    # Everything else: ambiguous shape, don't force a chart.
    return None


def _bar_chart_config(columns: list[str], rows: list[dict], analysis: ResultAnalysis) -> ChartConfig:
    categorical_cols = _find_columns_by_type(analysis.column_summaries, "categorical")
    numeric_cols = _find_columns_by_type(analysis.column_summaries, "numeric")
    cat_col = categorical_cols[0].name
    num_col = numeric_cols[0].name

    sorted_rows = sorted(rows, key=lambda r: (r.get(num_col) or 0), reverse=True)

    truncated_note = ""
    if len(sorted_rows) > MAX_CATEGORIES_FOR_BAR:
        top_rows = sorted_rows[:TOP_N_WHEN_TOO_MANY_CATEGORIES]
        others_sum = sum((r.get(num_col) or 0) for r in sorted_rows[TOP_N_WHEN_TOO_MANY_CATEGORIES:])
        top_rows = top_rows + [{cat_col: "Other", num_col: others_sum}]
        sorted_rows = top_rows
        truncated_note = f" (top {TOP_N_WHEN_TOO_MANY_CATEGORIES}, remainder grouped as 'Other')"

    return ChartConfig(
        chart_type=ChartType.BAR,
        title=f"{num_col} by {cat_col}{truncated_note}",
        data=[{
            "type": "bar",
            "x": [r.get(cat_col) for r in sorted_rows],
            "y": [r.get(num_col) for r in sorted_rows],
        }],
        layout={"xaxis": {"title": cat_col}, "yaxis": {"title": num_col}},
    )


def _line_chart_config(columns: list[str], rows: list[dict], analysis: ResultAnalysis) -> ChartConfig:
    datetime_cols = _find_columns_by_type(analysis.column_summaries, "datetime")
    numeric_cols = _find_columns_by_type(analysis.column_summaries, "numeric")
    date_col = datetime_cols[0].name

    sorted_rows = sorted(rows, key=lambda r: str(r.get(date_col) or ""))

    traces = [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "name": num.name,
            "x": [r.get(date_col) for r in sorted_rows],
            "y": [r.get(num.name) for r in sorted_rows],
        }
        for num in numeric_cols
    ]

    return ChartConfig(
        chart_type=ChartType.LINE,
        title=f"{', '.join(n.name for n in numeric_cols)} over {date_col}",
        data=traces,
        layout={"xaxis": {"title": date_col}, "yaxis": {"title": "Value"}},
    )


def _scatter_chart_config(columns: list[str], rows: list[dict], analysis: ResultAnalysis) -> ChartConfig:
    numeric_cols = _find_columns_by_type(analysis.column_summaries, "numeric")
    x_col, y_col = numeric_cols[0].name, numeric_cols[1].name

    return ChartConfig(
        chart_type=ChartType.SCATTER,
        title=f"{y_col} vs {x_col}",
        data=[{
            "type": "scatter",
            "mode": "markers",
            "x": [r.get(x_col) for r in rows],
            "y": [r.get(y_col) for r in rows],
        }],
        layout={"xaxis": {"title": x_col}, "yaxis": {"title": y_col}},
    )


def build_chart_config(
    chart_type: ChartType,
    columns: list[str],
    rows: list[dict],
    analysis: ResultAnalysis,
) -> ChartConfig:
    """
    Dispatches to the config builder for the given chart type. Kept
    separate from decide_chart_type() so the decision (what to chart)
    and the construction (how to build the Plotly spec) can be
    reasoned about and tested independently.
    """
    if chart_type == ChartType.BAR:
        return _bar_chart_config(columns, rows, analysis)
    if chart_type == ChartType.LINE:
        return _line_chart_config(columns, rows, analysis)
    if chart_type == ChartType.SCATTER:
        return _scatter_chart_config(columns, rows, analysis)
    raise ValueError(f"No config builder implemented for chart type: {chart_type}")