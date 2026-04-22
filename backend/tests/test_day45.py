"""
Full Integration Test for Week 2 Day 4-5.
Iterates 10 real-world benchmark queries through the full LangGraph pipeline.
Verifies logging, result formatting, and SQL correctness.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.graph import run_query
from db.connection import create_pool, close_pool

# The benchmark list of queries from the task spec
QUERIES = [
    "How many customers are there?",
    "What are the top 5 product categories by number of orders?",
    "What is the average order value?",
    "Which sellers have the most orders?",
    "Show me orders from São Paulo",
    "What is the average review score?",
    "How many orders were delivered late?",
    "What are the most common payment types?",
    "Show monthly revenue for 2017",
    "Which products have the lowest review scores?",
]

async def main():
    await create_pool()

    print("\n" + "=" * 60)
    print("STARTING FULL PIPELINE BENCHMARK (10 QUERIES)")
    print("=" * 60 + "\n")

    success_count = 0

    for i, q in enumerate(QUERIES, 1):
        print(f"\n[Q{i}/10] {q}")
        print("-" * 60)
        
        result = await run_query(q)
        
        success = result.get("success", False)
        answer = result.get("final_answer", "")
        sql = result.get("final_sql", "")
        retries = result.get("retry_count", 0)
        latency = result.get("latency_ms", 0)

        status_flag = "✅ PASS" if success else "❌ FAIL"
        if success:
            success_count += 1
            
        print(f"Status  : {status_flag}")
        print(f"Retries : {retries}")
        print(f"Latency : {latency:.0f} ms")
        print(f"SQL     : {sql}")
        print(f"Answer  : {answer}")

    print("\n" + "=" * 60)
    print(f"BENCHMARK COMPLETED: {success_count}/{len(QUERIES)} PASSED")
    print("=" * 60)

    await close_pool()

    return success_count == len(QUERIES)


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
