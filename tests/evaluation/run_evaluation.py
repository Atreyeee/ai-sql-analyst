"""
Runs the full benchmark dataset against the live /ask pipeline and
produces an aggregate evaluation report.

Calls the pipeline IN-PROCESS (importing directly from app.*) rather
than over HTTP, so this can run in CI without a live server — though
it still needs a live database and a valid Gemini API key.
"""

import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.ai.correction import run_with_correction
from app.ai.generator_base import SQLGenerator
from app.ai.llm_generator import LLMSQLGenerator
from app.ai.keyword_retriever import KeywordSchemaRetriever
from app.database.connection import get_engine
from app.database.inspector import get_schema_info
from tests.evaluation.checks import run_checks

BENCHMARK_PATH = Path(__file__).parent / "benchmark_questions.json"
REPORT_PATH = Path(__file__).parent / "evaluation_report.json"


def run_single_question(question_entry: dict, generator: SQLGenerator, retriever) -> dict:
    question = question_entry["question"]
    full_schema = get_schema_info(get_engine())
    relevant_schema = retriever.retrieve(question, full_schema)

    start = time.monotonic()
    result = run_with_correction(question, relevant_schema, generator)
    latency_ms = int((time.monotonic() - start) * 1000)

    execution = result.execution
    result_dict = {
        "columns": execution.columns,
        "rows": execution.rows,
        "row_count": execution.row_count,
    }

    checks_passed = False
    failures: list[str] = []
    if execution.success:
        checks_passed, failures = run_checks(result_dict, question_entry["expected_checks"])

    return {
        "id": question_entry["id"],
        "category": question_entry["category"],
        "question": question,
        "execution_success": execution.success,
        "result_correct": checks_passed,
        "correction_attempts": len(result.attempts),
        "latency_ms": latency_ms,
        "error": execution.error,
        "check_failures": failures,
    }


def aggregate_metrics(results: list[dict]) -> dict:
    n = len(results)
    execution_successes = sum(1 for r in results if r["execution_success"])
    result_correct = sum(1 for r in results if r["result_correct"])
    corrected = sum(1 for r in results if r["correction_attempts"] > 0)
    latencies = [r["latency_ms"] for r in results]

    by_category: dict[str, dict] = {}
    for r in results:
        cat = r["category"]
        by_category.setdefault(cat, {"total": 0, "correct": 0})
        by_category[cat]["total"] += 1
        if r["result_correct"]:
            by_category[cat]["correct"] += 1

    return {
        "total_questions": n,
        "sql_execution_success_rate": round(execution_successes / n, 3),
        "result_correctness_rate": round(result_correct / n, 3),
        "correction_rate": round(corrected / n, 3),
        "average_latency_ms": round(statistics.mean(latencies), 1),
        "p95_latency_ms": round(statistics.quantiles(latencies, n=20)[18], 1) if n >= 20 else max(latencies),
        "by_category": {
            cat: {
                "accuracy": round(v["correct"] / v["total"], 3),
                "total": v["total"],
            }
            for cat, v in by_category.items()
        },
    }


def main():
    questions = json.loads(BENCHMARK_PATH.read_text())
    generator: SQLGenerator = LLMSQLGenerator()
    retriever = KeywordSchemaRetriever()

    print(f"Running {len(questions)} benchmark questions...\n")
    results = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {q['id']}: {q['question']}")
        result = run_single_question(q, generator, retriever)
        status = "PASS" if result["result_correct"] else "FAIL"
        print(f"    -> {status} ({result['latency_ms']}ms, {result['correction_attempts']} corrections)")
        if result["check_failures"]:
            print(f"    -> reasons: {result['check_failures']}")
        results.append(result)

    metrics = aggregate_metrics(results)

    report = {"metrics": metrics, "results": results}
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str))

    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(f"SQL execution success rate: {metrics['sql_execution_success_rate']:.1%}")
    print(f"Result correctness rate:    {metrics['result_correctness_rate']:.1%}")
    print(f"Correction rate:            {metrics['correction_rate']:.1%}")
    print(f"Average latency:            {metrics['average_latency_ms']}ms")
    print(f"P95 latency:                {metrics['p95_latency_ms']}ms")
    print("\nBy category:")
    for cat, v in metrics["by_category"].items():
        print(f"  {cat:20s} {v['accuracy']:.1%}  (n={v['total']})")
    print(f"\nFull report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()