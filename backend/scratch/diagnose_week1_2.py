import asyncio
import sys
import os
import json

# Add root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.connection import get_pool, close_pool
from agents.nodes import schema_retriever, sql_generator, _format_schema_for_prompt
from agents.state import QueryState

async def analyze_schema_retrieval(question: str):
    print(f"\n--- Question: {question} ---")
    state: QueryState = {
        "user_question": question,
        "trace_steps": [],
        "retry_count": 0
    }
    
    # Run retriever
    result = await schema_retriever(state)
    retrieved_schema = result["retrieved_schema"]
    
    print("\n[RETRIEVED SCHEMA CONTENT]")
    for table, cols in retrieved_schema.items():
        print(f"Table: {table}")
        for col in cols:
            desc = col.get('description', '')
            print(f"  - {col['column']}: {desc[:60]}...")
            
    formatted = _format_schema_for_prompt(retrieved_schema)
    print("\n[FORMATTED FOR PROMPT]")
    print(formatted)
    
    return retrieved_schema

async def check_database_counts():
    pool = await get_pool()
    tables = [
        "olist_customers", "olist_orders", "olist_order_items", 
        "olist_products", "olist_sellers", "olist_order_payments", 
        "olist_order_reviews", "olist_geolocation", "product_category_translation"
    ]
    print("\n[DATABASE ROW COUNTS]")
    for table in tables:
        count = await pool.fetchval(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:35} : {count:,}")
    
    # Also check schema_embeddings
    se_count = await pool.fetchval("SELECT COUNT(*) FROM schema_embeddings")
    print(f"  {'schema_embeddings':35} : {se_count:,}")
    
    # Check query_logs
    ql_count = await pool.fetchval("SELECT COUNT(*) FROM query_logs")
    print(f"  {'query_logs':35} : {ql_count:,}")

async def main():
    await check_database_counts()
    
    questions = [
        "What are the top 5 product categories by number of orders?",
        "Show me orders from São Paulo"
    ]
    
    for q in questions:
        await analyze_schema_retrieval(q)
    
    await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
