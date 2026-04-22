"""
QueryMind — 20-Query Accuracy Benchmark

Sends 20 predefined business questions through the live /query API,
records success/fail, retries, latency, and generated SQL for each,
then generates a benchmark_report.json summary.

Usage:
    python tests/benchmark/benchmark_queries.py

Requires the FastAPI backend to be running on http://localhost:8000.
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required.  pip install httpx")
    sys.exit(1)

# ── Configuration ────────────────────────────────────────
API_URL = "http://localhost:8000/query?include_trace=true"
TIMEOUT = 120  # seconds per query (some JOINs are slow)
REPORT_PATH = Path(__file__).parent / "benchmark_report.json"

# ── 20 Benchmark Queries ────────────────────────────────
# Categories: Simple SELECT, Aggregation, JOIN, GROUP BY,
#             Date filtering, Subquery, Multi-join
BENCHMARK_QUERIES = [
    # --- Simple SELECT (1-3) ---
    {
        "id": 1,
        "category": "Simple SELECT",
        "question": "How many customers are there in the database?",
        "expect_rows": True,
    },
    {
        "id": 2,
        "category": "Simple SELECT",
        "question": "How many orders are there?",
        "expect_rows": True,
    },
    {
        "id": 3,
        "category": "Simple SELECT",
        "question": "How many products are in the catalog?",
        "expect_rows": True,
    },

    # --- Aggregation (4-6) ---
    {
        "id": 4,
        "category": "Aggregation",
        "question": "What is the average payment value across all orders?",
        "expect_rows": True,
    },
    {
        "id": 5,
        "category": "Aggregation",
        "question": "What is the total revenue from all order payments?",
        "expect_rows": True,
    },
    {
        "id": 6,
        "category": "Aggregation",
        "question": "What is the maximum price of any product sold?",
        "expect_rows": True,
    },

    # --- GROUP BY (7-10) ---
    {
        "id": 7,
        "category": "GROUP BY",
        "question": "What are the top 5 cities with the most customers?",
        "expect_rows": True,
    },
    {
        "id": 8,
        "category": "GROUP BY",
        "question": "How many orders are there for each order status?",
        "expect_rows": True,
    },
    {
        "id": 9,
        "category": "GROUP BY",
        "question": "What are the top 5 product categories by number of items sold?",
        "expect_rows": True,
    },
    {
        "id": 10,
        "category": "GROUP BY",
        "question": "Which payment type is used most often?",
        "expect_rows": True,
    },

    # --- JOIN (11-14) ---
    {
        "id": 11,
        "category": "JOIN",
        "question": "How many orders were placed by customers from Sao Paulo?",
        "expect_rows": True,
    },
    {
        "id": 12,
        "category": "JOIN",
        "question": "What is the average review score for delivered orders?",
        "expect_rows": True,
    },
    {
        "id": 13,
        "category": "JOIN",
        "question": "Which seller has sold the most items?",
        "expect_rows": True,
    },
    {
        "id": 14,
        "category": "JOIN",
        "question": "What is the average freight cost per order?",
        "expect_rows": True,
    },

    # --- Date Filtering (15-17) ---
    {
        "id": 15,
        "category": "Date Filtering",
        "question": "How many orders were placed in the year 2017?",
        "expect_rows": True,
    },
    {
        "id": 16,
        "category": "Date Filtering",
        "question": "What month had the highest number of orders?",
        "expect_rows": True,
    },
    {
        "id": 17,
        "category": "Date Filtering",
        "question": "How many orders were delivered late, meaning the delivery date was after the estimated delivery date?",
        "expect_rows": True,
    },

    # --- Multi-Join / Complex (18-20) ---
    {
        "id": 18,
        "category": "Multi-Join",
        "question": "What are the top 3 product categories by total revenue?",
        "expect_rows": True,
    },
    {
        "id": 19,
        "category": "Multi-Join",
        "question": "Which state has the highest average order value?",
        "expect_rows": True,
    },
    {
        "id": 20,
        "category": "Multi-Join",
        "question": "What is the average number of items per order?",
        "expect_rows": True,
    },
]


def run_benchmark():
    """Execute all 20 benchmark queries and collect results."""
    results = []
    total_start = time.time()

    print("=" * 70)
    print("  QueryMind — 20-Query Accuracy Benchmark")
    print("=" * 70)
    print(f"  Target: {API_URL}")
    print(f"  Queries: {len(BENCHMARK_QUERIES)}")
    print(f"  Timeout: {TIMEOUT}s per query")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    with httpx.Client(timeout=TIMEOUT) as client:
        for q in BENCHMARK_QUERIES:
            qid = q["id"]
            category = q["category"]
            question = q["question"]

            print(f"  [{qid:2d}/20] [{category:<15s}] {question[:60]}...")

            start = time.time()
            try:
                resp = client.post(
                    API_URL,
                    json={"question": question},
                )
                elapsed_ms = (time.time() - start) * 1000
                data = resp.json()

                success = data.get("metrics", {}).get("success", False)
                retries = data.get("metrics", {}).get("retries", 0)
                latency = data.get("metrics", {}).get("latency_ms", 0)
                sql = data.get("sql", "")
                answer = data.get("answer", "")
                error = data.get("error")
                row_count = len(data.get("rows", []))

                # Determine pass/fail
                if success and (not q["expect_rows"] or row_count > 0):
                    status = "PASS"
                    passed += 1
                    print(f"           [PASS] | {row_count} rows | {retries} retries | {latency:.0f}ms")
                else:
                    status = "FAIL"
                    failed += 1
                    err_short = (error or "No rows returned")[:80]
                    print(f"           [FAIL] | {err_short}")

                results.append({
                    "id": qid,
                    "category": category,
                    "question": question,
                    "status": status,
                    "success": success,
                    "sql": sql,
                    "answer_preview": answer[:200],
                    "row_count": row_count,
                    "retries": retries,
                    "latency_ms": round(latency, 2),
                    "client_elapsed_ms": round(elapsed_ms, 2),
                    "error": error,
                })

            except httpx.TimeoutException:
                elapsed_ms = (time.time() - start) * 1000
                failed += 1
                print(f"           [TIME] TIMEOUT after {elapsed_ms:.0f}ms")
                results.append({
                    "id": qid,
                    "category": category,
                    "question": question,
                    "status": "TIMEOUT",
                    "success": False,
                    "sql": "",
                    "answer_preview": "",
                    "row_count": 0,
                    "retries": 0,
                    "latency_ms": 0,
                    "client_elapsed_ms": round(elapsed_ms, 2),
                    "error": "Client timeout",
                })

            except Exception as e:
                elapsed_ms = (time.time() - start) * 1000
                failed += 1
                print(f"           [ERR]  | {str(e)[:80]}")
                results.append({
                    "id": qid,
                    "category": category,
                    "question": question,
                    "status": "ERROR",
                    "success": False,
                    "sql": "",
                    "answer_preview": "",
                    "row_count": 0,
                    "retries": 0,
                    "latency_ms": 0,
                    "client_elapsed_ms": round(elapsed_ms, 2),
                    "error": str(e),
                })

            print()

    total_elapsed = time.time() - total_start

    # ── Summary ──────────────────────────────────────────
    pass_rate = (passed / len(BENCHMARK_QUERIES)) * 100
    avg_latency = (
        sum(r["latency_ms"] for r in results if r["status"] == "PASS")
        / max(passed, 1)
    )
    avg_retries = (
        sum(r["retries"] for r in results) / len(results)
    )

    summary = {
        "total_queries": len(BENCHMARK_QUERIES),
        "passed": passed,
        "failed": failed,
        "pass_rate_percent": round(pass_rate, 1),
        "avg_latency_ms": round(avg_latency, 1),
        "avg_retries": round(avg_retries, 2),
        "total_benchmark_time_seconds": round(total_elapsed, 1),
        "timestamp": datetime.now().isoformat(),
    }

    report = {
        "summary": summary,
        "results": results,
    }

    # ── Write Report ─────────────────────────────────────
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=" * 70)
    print("  BENCHMARK COMPLETE")
    print("=" * 70)
    print(f"  Passed:       {passed}/{len(BENCHMARK_QUERIES)}")
    print(f"  Failed:       {failed}/{len(BENCHMARK_QUERIES)}")
    print(f"  Pass Rate:    {pass_rate:.1f}%")
    print(f"  Avg Latency:  {avg_latency:.0f}ms (passing queries)")
    print(f"  Avg Retries:  {avg_retries:.2f}")
    print(f"  Total Time:   {total_elapsed:.1f}s")
    print(f"  Report:       {REPORT_PATH}")
    print("=" * 70)

    return pass_rate


if __name__ == "__main__":
    rate = run_benchmark()
    sys.exit(0 if rate >= 70 else 1)
