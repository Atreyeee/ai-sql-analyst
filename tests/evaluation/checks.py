"""
Check functions: given an AskResponse-shaped result, determine
whether it satisfies an expected_check from the benchmark dataset.

Each check function is intentionally narrow and independently
testable. We check RESULT PROPERTIES, not exact values or exact SQL —
see benchmark_questions.json's docstring-equivalent comment for why.
"""

from typing import Any


def check_row_count_equals(result: dict, check: dict) -> bool:
    return result.get("row_count") == check["value"]


def check_row_count_between(result: dict, check: dict) -> bool:
    row_count = result.get("row_count", -1)
    return check["min"] <= row_count <= check["max"]


def check_column_exists(result: dict, check: dict) -> bool:
    columns = [c.lower() for c in result.get("columns", [])]
    if "column" in check:
        return check["column"].lower() in columns
    if "column_hint" in check:
        return any(check["column_hint"].lower() in c for c in columns)
    return False


def check_column_exists_hint(result: dict, check: dict) -> bool:
    columns = [c.lower() for c in result.get("columns", [])]
    return any(any(hint.lower() in c for c in columns) for hint in check["hints"])


def check_numeric_column_positive(result: dict, check: dict) -> bool:
    """
    Finds a numeric column whose name matches the hint, and confirms
    its value (in the first row) is positive. Used for revenue/sum-type
    aggregate checks where the exact column name may vary.
    """
    hint_pattern = check.get("column_hint", "")
    rows = result.get("rows", [])
    if not rows:
        return False
    first_row = rows[0]
    for col_name, value in first_row.items():
        if any(h in col_name.lower() for h in hint_pattern.split("|")):
            try:
                return float(value) > 0
            except (TypeError, ValueError):
                continue
    return False


CHECK_REGISTRY = {
    "row_count_equals": check_row_count_equals,
    "row_count_between": check_row_count_between,
    "column_exists": check_column_exists,
    "column_exists_hint": check_column_exists_hint,
    "numeric_column_positive": check_numeric_column_positive,
}


def run_checks(result: dict, expected_checks: list[dict]) -> tuple[bool, list[str]]:
    """
    Runs every expected_check against the result. Returns (all_passed,
    list of failure reasons) — we collect ALL failures, not just the
    first, so a benchmark report shows the full picture per question.
    """
    failures = []
    for check in expected_checks:
        check_type = check["type"]
        check_fn = CHECK_REGISTRY.get(check_type)
        if check_fn is None:
            failures.append(f"Unknown check type: {check_type}")
            continue
        if not check_fn(result, check):
            failures.append(f"Failed check: {check}")
    return len(failures) == 0, failures