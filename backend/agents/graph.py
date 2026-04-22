"""
Defines the StateGraph for the execution pipeline.
Wires the 8 nodes together with conditional routing.
"""

import time
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END

from agents.state import QueryState
from agents.nodes import (
    schema_retriever,
    sql_generator,
    sql_validator,
    sql_executor,
    sql_corrector,
    failure_handler,
    result_formatter,
    query_logger,
)
from config import MAX_RETRIES

logger = logging.getLogger("querymind.agents.graph")


def build_graph() -> StateGraph:
    """Builds and compiles the QueryMind execution graph."""
    
    workflow = StateGraph(QueryState)

    # 1. Add all nodes
    workflow.add_node("schema_retriever", schema_retriever)
    workflow.add_node("sql_generator", sql_generator)
    workflow.add_node("sql_validator", sql_validator)
    workflow.add_node("sql_executor", sql_executor)
    workflow.add_node("sql_corrector", sql_corrector)
    workflow.add_node("failure_handler", failure_handler)
    workflow.add_node("result_formatter", result_formatter)
    workflow.add_node("query_logger", query_logger)

    # 2. Define the main execution path
    workflow.add_edge(START, "schema_retriever")
    workflow.add_edge("schema_retriever", "sql_generator")
    workflow.add_edge("sql_generator", "sql_validator")

    # 3. Define conditional routing from the validator
    def route_from_validator(state: QueryState) -> str:
        if state.get("error_message"):
            return "sql_corrector"
        return "sql_executor"

    workflow.add_conditional_edges(
        "sql_validator",
        route_from_validator,
        {
            "sql_corrector": "sql_corrector",
            "sql_executor": "sql_executor"
        }
    )

    # 4. Define conditional routing from the executor
    def route_from_executor(state: QueryState) -> str:
        if state.get("success"):
            return "result_formatter"
        return "sql_corrector"

    workflow.add_conditional_edges(
        "sql_executor",
        route_from_executor,
        {
            "result_formatter": "result_formatter",
            "sql_corrector": "sql_corrector"
        }
    )

    # 5. Define conditional routing from the corrector
    def route_from_corrector(state: QueryState) -> str:
        if state.get("retry_count", 0) >= MAX_RETRIES:
            return "failure_handler"
        return "sql_validator"

    workflow.add_conditional_edges(
        "sql_corrector",
        route_from_corrector,
        {
            "failure_handler": "failure_handler",
            "sql_validator": "sql_validator"
        }
    )

    # 6. Both successful paths and failure paths converge to the logger
    workflow.add_edge("result_formatter", "query_logger")
    workflow.add_edge("failure_handler", "query_logger")
    
    # 7. Logger goes to END
    workflow.add_edge("query_logger", END)

    logger.info("Compiling StateGraph...")
    return workflow.compile()


# Create the compiled graph instance
graph = build_graph()


async def run_query(question: str) -> Dict[str, Any]:
    """
    Main entry point to execute the full LangGraph pipeline.

    Args:
        question: User's natural language question.

    Returns:
        The final state dict containing the final answer, SQL, and logs.
    """
    logger.info("============= STARTING QUERY PIPELINE =============")
    logger.info("Question: %s", question)
    
    initial_state = {
        "user_question": question,
        "start_time": time.time(),
        "trace_steps": [],
        "retry_count": 0,
    }

    try:
        # LangGraph invoke returns the final dictionary state
        final_state = await graph.ainvoke(initial_state)
        logger.info("Pipeline completed successfully")
        return final_state
    except Exception as e:
        logger.error("Pipeline crashed catastrophically: %s", e, exc_info=True)
        return {
            "success": False,
            "final_answer": "An unexpected critical error occurred: " + str(e),
        }
