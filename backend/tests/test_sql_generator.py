"""
Manual test for Week 2 Day 1: sql_generator node.

Tests:
  1. sql_generator with mock schema (no DB needed, just Groq API)
  2. Full chain: schema_retriever → sql_generator (needs DB + Groq)
"""

import asyncio
import sys
import os

# Ensure backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.nodes import sql_generator, schema_retriever, _clean_sql_response
from db.connection import create_pool, close_pool


# ── Test 1: _clean_sql_response helper ──────────────────────
def test_clean_sql_response():
    """Verify the SQL cleaner strips markdown fences and backticks."""
    cases = [
        # (input, expected substring)
        ("```sql\nSELECT COUNT(*) FROM orders\n```", "SELECT COUNT(*) FROM orders"),
        ("```\nSELECT 1\n```", "SELECT 1"),
        ("`SELECT 1`", "SELECT 1"),
        ("Here is the query:\nSELECT 1 FROM t", "SELECT 1 FROM t"),
        ("SELECT 1;", "SELECT 1"),
    ]
    print("\n── Test 1: _clean_sql_response ──")
    all_ok = True
    for raw, expected in cases:
        result = _clean_sql_response(raw)
        ok = expected in result
        status = "✓" if ok else "✗"
        print(f"  {status}  {repr(raw)[:50]}  →  {repr(result)[:50]}")
        if not ok:
            all_ok = False
    return all_ok


# ── Test 2: sql_generator with mock schema ──────────────────
async def test_sql_generator_mock_schema():
    """Call sql_generator with a hand-crafted schema (no DB)."""
    print("\n── Test 2: sql_generator with mock schema ──")

    mock_state = {
        "user_question": "How many orders were placed?",
        "retrieved_schema": {
            "olist_orders": [
                {"column": "order_id", "description": "Unique order identifier"},
                {"column": "order_status", "description": "Current status of the order"},
                {"column": "order_purchase_timestamp", "description": "Timestamp when the order was placed"},
            ]
        },
        "trace_steps": [],
    }

    result = await sql_generator(mock_state)
    sql = result.get("generated_sql", "")
    print(f"  Question : {mock_state['user_question']}")
    print(f"  SQL      : {sql}")

    # Basic validations
    checks = {
        "SQL is non-empty": len(sql) > 0,
        "Contains SELECT": "SELECT" in sql.upper(),
        "References olist_orders": "olist_orders" in sql.lower(),
        "Contains COUNT": "COUNT" in sql.upper(),
        "No markdown backticks": "```" not in sql,
        "trace_steps updated": len(result.get("trace_steps", [])) > 0,
    }

    all_ok = True
    for label, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status}  {label}")
        if not passed:
            all_ok = False
    return all_ok


# ── Test 3: Full chain (schema_retriever → sql_generator) ──
async def test_full_chain():
    """End-to-end: retrieve real schema from DB then generate SQL."""
    print("\n── Test 3: Full chain (schema_retriever → sql_generator) ──")

    questions = [
        "How many orders were placed?",
        "What are the top 5 product categories by number of orders?",
        "What is the average order value?",
    ]

    # Need a live DB pool for schema_retriever
    await create_pool()

    all_ok = True
    for q in questions:
        initial_state = {
            "user_question": q,
            "retrieved_schema": {},
            "trace_steps": [],
        }

        # Step 1: schema_retriever
        retriever_result = await schema_retriever(initial_state)
        merged = {**initial_state, **retriever_result}

        # Step 2: sql_generator
        generator_result = await sql_generator(merged)
        sql = generator_result.get("generated_sql", "")

        ok = len(sql) > 0 and "SELECT" in sql.upper()
        status = "✓" if ok else "✗"
        print(f"  {status}  Q: {q}")
        print(f"       SQL: {sql}")
        if not ok:
            all_ok = False

    await close_pool()
    return all_ok


# ── Main ─────────────────────────────────────────────────────
async def main():
    results = {}

    # Test 1: synchronous
    results["clean_sql"] = test_clean_sql_response()

    # Test 2: async (Groq API only)
    results["mock_schema"] = await test_sql_generator_mock_schema()

    # Test 3: async (DB + Groq)
    results["full_chain"] = await test_full_chain()

    # Summary
    print("\n" + "=" * 50)
    print("Week 2 Day 1 — Test Summary")
    print("=" * 50)
    for name, passed in results.items():
        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"  {status}  {name}")

    all_passed = all(results.values())
    print(f"\nOverall: {'ALL PASSED ✓' if all_passed else 'SOME FAILED ✗'}")
    return all_passed


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
