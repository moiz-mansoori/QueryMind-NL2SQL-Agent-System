"""
Temporary test for schema retriever node.
"""
import asyncio
import logging
from pprint import pprint

from agents.state import QueryState
from agents.nodes import schema_retriever
from db.connection import close_pool

logging.basicConfig(level=logging.INFO)

async def main():
    state: QueryState = {
        "user_question": "What is the average review score for top selling products?",
        "retrieved_schema": {},
        "generated_sql": "",
        "final_sql": "",
        "error_message": None,
        "retry_count": 0,
        "result_data": [],
        "success": False,
        "final_answer": "",
        "start_time": 0.0,
        "latency_ms": 0.0,
        "trace_steps": []
    }
    
    print(f"Testing schema_retriever with question: '{state['user_question']}'")
    result_state = await schema_retriever(state)
    
    print("\nRETRIEVED SCHEMA:")
    pprint(result_state.get("retrieved_schema"))
    
    print("\nTRACE STEPS:")
    pprint(result_state.get("trace_steps"))
    
    # Close pool safely
    await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
