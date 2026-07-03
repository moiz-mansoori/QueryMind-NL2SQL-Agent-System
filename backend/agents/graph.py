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
    query_classifier,
    direct_responder,
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
    workflow.add_node("query_classifier", query_classifier)
    workflow.add_node("direct_responder", direct_responder)
    workflow.add_node("schema_retriever", schema_retriever)
    workflow.add_node("sql_generator", sql_generator)
    workflow.add_node("sql_validator", sql_validator)
    workflow.add_node("sql_executor", sql_executor)
    workflow.add_node("sql_corrector", sql_corrector)
    workflow.add_node("failure_handler", failure_handler)
    workflow.add_node("result_formatter", result_formatter)
    workflow.add_node("query_logger", query_logger)

    # 2. Define the main execution path
    workflow.add_edge(START, "query_classifier")
    
    def route_from_classifier(state: QueryState) -> str:
        intent = state.get("intent", "database_query")
        if intent == "database_query":
            return "schema_retriever"
        return "direct_responder"

    workflow.add_conditional_edges(
        "query_classifier",
        route_from_classifier,
        {
            "schema_retriever": "schema_retriever",
            "direct_responder": "direct_responder"
        }
    )
    
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

    # 6. Both successful paths, failure paths, and direct responses converge to the logger
    workflow.add_edge("result_formatter", "query_logger")
    workflow.add_edge("failure_handler", "query_logger")
    workflow.add_edge("direct_responder", "query_logger")
    
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


async def run_query_stream(question: str):
    """
    Execute the LangGraph pipeline and yield state updates after each node completes.
    """
    logger.info("============= STARTING STREAMING QUERY PIPELINE =============")
    logger.info("Question: %s", question)
    
    initial_state = {
        "user_question": question,
        "start_time": time.time(),
        "trace_steps": [],
        "retry_count": 0,
    }

    try:
        # Accumulate the state as updates flow in
        current_state = dict(initial_state)
        last_node_time = time.time()
        
        async for event in graph.astream(initial_state, stream_mode="updates"):
            # event is a dict of {node_name: node_update_dict}
            for node_name, updates in event.items():
                current_time = time.time()
                duration_ms = round((current_time - last_node_time) * 1000, 2)
                last_node_time = current_time
                
                current_state.update(updates)
                
                # Retrieve trace steps and inject duration
                trace_steps = list(current_state.get("trace_steps", []))
                if trace_steps and trace_steps[-1]["node"] == node_name:
                    trace_steps[-1]["duration_ms"] = duration_ms
                    current_state["trace_steps"] = trace_steps
                
                # Fetch metadata context details from the step trace
                step_trace = trace_steps[-1] if trace_steps else {}

                # Yield the node completion event and the latest trace/state details
                yield {
                    "type": "node_complete",
                    "node": node_name,
                    "duration_ms": duration_ms,
                    "trace_steps": trace_steps,
                    "success": current_state.get("success", False),
                    "retry_count": current_state.get("retry_count", 0),
                    "metadata": {
                        "intent": current_state.get("intent"),
                        "retrieved_tables_count": step_trace.get("retrieved_tables_count"),
                        "row_count": step_trace.get("row_count"),
                        "error": step_trace.get("error") or current_state.get("error_message"),
                    }
                }
        
        # Finally, yield the complete state
        yield {
            "type": "complete",
            "answer": current_state.get("final_answer", ""),
            "sql": current_state.get("final_sql") or current_state.get("generated_sql", ""),
            "rows": current_state.get("result_data", []),
            "metrics": {
                "retries": current_state.get("retry_count", 0),
                "latency_ms": round((time.time() - current_state["start_time"]) * 1000, 2) if "start_time" in current_state else 0,
                "success": current_state.get("success", False),
            },
            "error": current_state.get("error_message") if not current_state.get("success", False) else None,
            "trace_steps": current_state.get("trace_steps", []),
        }

    except Exception as e:
        logger.error("Streaming pipeline crashed catastrophically: %s", e, exc_info=True)
        yield {
            "event": "error",
            "error": f"Critical error: {str(e)}"
        }
