"""
Manual test for Week 2 Day 2: sql_validator + sql_executor nodes.

Tests:
  1. sql_validator — syntax errors, dangerous keywords, unknown tables, valid SQL
  2. sql_executor — happy path execution against live DB
  3. Full 4-node chain: schema_retriever -> sql_generator -> sql_validator -> sql_executor
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.nodes import sql_validator, sql_executor, schema_retriever, sql_generator
from db.connection import create_pool, close_pool


# ── Test 1: sql_validator unit tests ─────────────────────────
async def test_sql_validator():
    """Validate the three layers of protection in sql_validator."""
    print("\n== Test 1: sql_validator ==")
    all_ok = True

    cases = [
        # (label, sql, should_pass)
        ("Valid SELECT",            "SELECT COUNT(*) FROM olist_orders",    True),
        ("Valid JOIN",              "SELECT o.order_id, c.city FROM olist_orders o JOIN olist_customers c ON o.customer_id = c.customer_id", True),
        ("Valid with GROUP BY",     "SELECT city, COUNT(*) FROM olist_customers GROUP BY city", True),
        ("Empty SQL",              "",                                      False),
        ("DROP TABLE blocked",     "DROP TABLE olist_orders",               False),
        ("DELETE blocked",         "DELETE FROM olist_orders WHERE 1=1",    False),
        ("TRUNCATE blocked",       "TRUNCATE olist_customers",              False),
        ("UPDATE blocked",         "UPDATE olist_orders SET order_status='x'", False),
        ("INSERT blocked",         "INSERT INTO olist_orders VALUES (1,2)", False),
        ("Unknown table",          "SELECT * FROM nonexistent_table",       False),
        ("Mixed known+unknown",    "SELECT * FROM olist_orders JOIN fake_table ON 1=1", False),
    ]

    for label, sql, should_pass in cases:
        state = {"generated_sql": sql, "trace_steps": []}
        result = await sql_validator(state)
        error = result.get("error_message")
        passed = (error is None) == should_pass
        status = "PASS" if passed else "FAIL"
        icon = "+" if passed else "!"
        detail = "OK" if error is None else error[:60]
        print(f"  [{icon}] {status}  {label:30s}  ->  {detail}")
        if not passed:
            all_ok = False

    return all_ok


# ── Test 2: sql_executor with a known-good query ─────────────
async def test_sql_executor():
    """Run a simple COUNT(*) against the live database."""
    print("\n== Test 2: sql_executor ==")

    await create_pool()

    state = {
        "generated_sql": "SELECT COUNT(*) AS total FROM olist_customers",
        "trace_steps": [],
        "retry_count": 0,
    }
    result = await sql_executor(state)

    checks = {
        "success is True":     result.get("success") is True,
        "error_message is None": result.get("error_message") is None,
        "result_data non-empty": len(result.get("result_data", [])) > 0,
        "total > 0":           (result.get("result_data", [{}])[0].get("total", 0) > 0),
        "trace logged":        any(s["node"] == "sql_executor" for s in result.get("trace_steps", [])),
    }

    all_ok = True
    for label, ok in checks.items():
        icon = "+" if ok else "!"
        status = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {status}  {label}")
        if not ok:
            all_ok = False

    if result.get("result_data"):
        print(f"       -> total customers: {result['result_data'][0].get('total')}")

    await close_pool()
    return all_ok


# ── Test 3: sql_executor with auto-LIMIT ──────────────────────
async def test_auto_limit():
    """Verify LIMIT is automatically appended when missing."""
    print("\n== Test 3: auto-LIMIT ==")

    await create_pool()

    state = {
        "generated_sql": "SELECT * FROM olist_customers",
        "trace_steps": [],
        "retry_count": 0,
    }
    result = await sql_executor(state)
    final_sql = result.get("final_sql", "")
    has_limit = "LIMIT" in final_sql.upper()
    row_count = len(result.get("result_data", []))

    checks = {
        "LIMIT injected":   has_limit,
        "rows <= 500":      row_count <= 500,
        "success":          result.get("success") is True,
    }

    all_ok = True
    for label, ok in checks.items():
        icon = "+" if ok else "!"
        status = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {status}  {label}")
        if not ok:
            all_ok = False

    print(f"       -> rows returned: {row_count}, final_sql LIMIT: {has_limit}")

    await close_pool()
    return all_ok


# ── Test 4: sql_executor error handling ────────────────────────
async def test_executor_error():
    """Verify the executor gracefully handles bad SQL."""
    print("\n== Test 4: executor error handling ==")

    await create_pool()

    state = {
        "generated_sql": "SELECT nonexistent_col FROM olist_orders",
        "trace_steps": [],
        "retry_count": 0,
    }
    result = await sql_executor(state)

    checks = {
        "success is False":       result.get("success") is False,
        "error_message set":      result.get("error_message") is not None,
        "retry_count incremented": result.get("retry_count", 0) == 1,
        "result_data empty":      len(result.get("result_data", [])) == 0,
    }

    all_ok = True
    for label, ok in checks.items():
        icon = "+" if ok else "!"
        status = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {status}  {label}")
        if not ok:
            all_ok = False

    await close_pool()
    return all_ok


# ── Test 5: Full 4-node chain ─────────────────────────────────
async def test_full_chain():
    """End-to-end: schema_retriever -> sql_generator -> sql_validator -> sql_executor"""
    print("\n== Test 5: Full 4-node chain ==")

    await create_pool()

    question = "How many customers are there?"
    state = {"user_question": question, "retrieved_schema": {}, "trace_steps": []}

    # Node 1: schema_retriever
    r1 = await schema_retriever(state)
    state = {**state, **r1}
    print(f"  [1] schema_retriever: {len(state.get('retrieved_schema', {}))} tables retrieved")

    # Node 2: sql_generator
    r2 = await sql_generator(state)
    state = {**state, **r2}
    sql = state.get("generated_sql", "")
    print(f"  [2] sql_generator:    {sql}")

    # Node 3: sql_validator
    r3 = await sql_validator(state)
    state = {**state, **r3}
    valid = state.get("error_message") is None
    print(f"  [3] sql_validator:    {'PASSED' if valid else 'FAILED - ' + str(state.get('error_message', ''))}")

    # Node 4: sql_executor (only if validation passed)
    if valid:
        r4 = await sql_executor(state)
        state = {**state, **r4}
        rows = state.get("result_data", [])
        print(f"  [4] sql_executor:    {len(rows)} rows returned, success={state.get('success')}")
        if rows:
            print(f"       -> first row: {rows[0]}")
    else:
        print(f"  [4] sql_executor:    SKIPPED (validation failed)")

    await close_pool()

    all_ok = valid and state.get("success", False)
    return all_ok


# ── Main ──────────────────────────────────────────────────────
async def main():
    results = {}

    results["sql_validator"] = await test_sql_validator()
    results["sql_executor"] = await test_sql_executor()
    results["auto_limit"] = await test_auto_limit()
    results["executor_error"] = await test_executor_error()
    results["full_chain"] = await test_full_chain()

    print("\n" + "=" * 50)
    print("Week 2 Day 2 - Test Summary")
    print("=" * 50)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        icon = "+" if passed else "!"
        print(f"  [{icon}] {status}  {name}")

    all_passed = all(results.values())
    print(f"\nOverall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    return all_passed


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
