"""
Manual test for Week 2 Day 3: sql_corrector + failure_handler nodes.

Tests:
  1. sql_corrector fixes a bad table name (validator error -> correction)
  2. sql_corrector fixes a bad column (executor error -> correction)
  3. failure_handler triggers after max retries
  4. Full correction loop: generate bad SQL -> correct -> validate -> execute
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.nodes import (
    sql_corrector, failure_handler, sql_validator, sql_executor,
    schema_retriever, sql_generator,
)
from db.connection import create_pool, close_pool
from config import MAX_RETRIES


# == Test 1: sql_corrector fixes a wrong table name ==
async def test_corrector_fixes_table():
    """Corrector should produce SQL with the right table after a table-not-found error."""
    print("\n== Test 1: sql_corrector fixes wrong table name ==")

    state = {
        "user_question": "How many customers are there?",
        "generated_sql": "SELECT COUNT(*) FROM customers",
        "error_message": "Validation failed: unknown table(s) referenced: customers. Known tables: olist_customers",
        "retrieved_schema": {
            "olist_customers": [
                {"column": "customer_id", "description": "Unique customer identifier"},
                {"column": "customer_unique_id", "description": "Unique customer ID across orders"},
            ]
        },
        "retry_count": 0,
        "trace_steps": [],
    }

    result = await sql_corrector(state)
    corrected = result.get("generated_sql", "")

    checks = {
        "SQL is non-empty":         len(corrected) > 0,
        "Contains olist_customers": "olist_customers" in corrected.lower(),
        "retry_count incremented":  result.get("retry_count") == 1,
        "error_message cleared":    result.get("error_message") is None,
        "trace_steps updated":      any(s["node"] == "sql_corrector" for s in result.get("trace_steps", [])),
    }

    all_ok = True
    for label, ok in checks.items():
        icon = "+" if ok else "!"
        print(f"  [{icon}] {'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            all_ok = False
    print(f"       -> corrected SQL: {corrected}")
    return all_ok


# == Test 2: sql_corrector fixes a bad column ==
async def test_corrector_fixes_column():
    """Corrector should fix a nonexistent column error from the executor."""
    print("\n== Test 2: sql_corrector fixes bad column ==")

    state = {
        "user_question": "What are the top cities?",
        "generated_sql": "SELECT city_name, COUNT(*) FROM olist_customers GROUP BY city_name",
        "error_message": 'SQL execution failed: column "city_name" does not exist',
        "retrieved_schema": {
            "olist_customers": [
                {"column": "customer_id", "description": "Unique customer identifier"},
                {"column": "customer_city", "description": "City of the customer"},
                {"column": "customer_state", "description": "State of the customer"},
            ]
        },
        "retry_count": 0,
        "trace_steps": [],
    }

    result = await sql_corrector(state)
    corrected = result.get("generated_sql", "")

    checks = {
        "SQL is non-empty":         len(corrected) > 0,
        "Contains customer_city":   "customer_city" in corrected.lower(),
        "No city_name anymore":     "city_name" not in corrected.lower(),
        "retry_count incremented":  result.get("retry_count") == 1,
    }

    all_ok = True
    for label, ok in checks.items():
        icon = "+" if ok else "!"
        print(f"  [{icon}] {'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            all_ok = False
    print(f"       -> corrected SQL: {corrected}")
    return all_ok


# == Test 3: failure_handler triggers correctly ==
async def test_failure_handler():
    """Failure handler should produce a user-friendly message."""
    print("\n== Test 3: failure_handler ==")

    state = {
        "user_question": "Show me something impossible",
        "generated_sql": "SELECT impossible FROM nowhere",
        "error_message": "column 'impossible' does not exist",
        "retry_count": MAX_RETRIES,
        "trace_steps": [],
    }

    result = await failure_handler(state)

    checks = {
        "success is False":      result.get("success") is False,
        "final_answer is set":   len(result.get("final_answer", "")) > 0,
        "mentions retry count":  str(MAX_RETRIES) in result.get("final_answer", ""),
        "mentions error":        "impossible" in result.get("final_answer", "").lower(),
        "trace terminal step":   any(s.get("status") == "terminal" for s in result.get("trace_steps", [])),
    }

    all_ok = True
    for label, ok in checks.items():
        icon = "+" if ok else "!"
        print(f"  [{icon}] {'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            all_ok = False
    print(f"       -> final_answer: {result.get('final_answer', '')[:100]}...")
    return all_ok


# == Test 4: Full correction loop (end-to-end with DB) ==
async def test_correction_loop():
    """Simulate: generate bad SQL -> corrector fixes it -> validator + executor succeed."""
    print("\n== Test 4: Full correction loop (with DB) ==")

    await create_pool()

    # Start with a deliberately wrong SQL (bad table name)
    state = {
        "user_question": "How many customers are there?",
        "generated_sql": "SELECT COUNT(*) FROM customers",  # wrong table!
        "retrieved_schema": {
            "olist_customers": [
                {"column": "customer_id", "description": "Unique customer identifier"},
                {"column": "customer_unique_id", "description": "Unique customer ID"},
            ]
        },
        "retry_count": 0,
        "error_message": None,
        "trace_steps": [],
    }

    # Step 1: Validator should catch the bad table
    r1 = await sql_validator(state)
    state = {**state, **r1}
    print(f"  [1] validator:  error={state.get('error_message', 'None')[:60]}")

    # Step 2: Corrector should fix it
    r2 = await sql_corrector(state)
    state = {**state, **r2}
    print(f"  [2] corrector:  sql={state.get('generated_sql', '')}")

    # Step 3: Validator again (should pass now)
    r3 = await sql_validator(state)
    state = {**state, **r3}
    valid = state.get("error_message") is None
    print(f"  [3] validator:  {'PASSED' if valid else 'FAILED - ' + str(state.get('error_message'))}")

    # Step 4: Executor (if validation passed)
    if valid:
        r4 = await sql_executor(state)
        state = {**state, **r4}
        rows = state.get("result_data", [])
        print(f"  [4] executor:   {len(rows)} rows, success={state.get('success')}")
        if rows:
            print(f"       -> first row: {rows[0]}")

    await close_pool()

    all_ok = valid and state.get("success", False)
    print(f"  -> Loop result: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


# == Main ==
async def main():
    results = {}
    results["corrector_table"] = await test_corrector_fixes_table()
    results["corrector_column"] = await test_corrector_fixes_column()
    results["failure_handler"] = await test_failure_handler()
    results["correction_loop"] = await test_correction_loop()

    print("\n" + "=" * 50)
    print("Week 2 Day 3 - Test Summary")
    print("=" * 50)
    for name, passed in results.items():
        icon = "+" if passed else "!"
        print(f"  [{icon}] {'PASS' if passed else 'FAIL'}  {name}")

    all_passed = all(results.values())
    print(f"\nOverall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    return all_passed


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
