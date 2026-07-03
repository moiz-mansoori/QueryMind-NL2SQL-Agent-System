import json
import time
import logging
from typing import Dict, Any

from db.connection import get_pool
from agents.state import QueryState

logger = logging.getLogger("querymind.agents.nodes.logger")

async def query_logger(state: QueryState) -> Dict[str, Any]:
    """
    Node 8: Logs the query execution to the database.
    """
    start_time = state.get("start_time", 0)
    latency_ms = (time.time() - start_time) * 1000 if start_time else 0
    trace_steps = list(state.get("trace_steps", []))

    user_question = state.get("user_question", "")
    generated_sql = state.get("generated_sql", "")
    final_sql = state.get("final_sql", "")
    result_data = state.get("result_data", [])
    error_msg = state.get("error_message") or None
    retry_count = state.get("retry_count", 0)
    success = state.get("success", False)

    logger.info(
        "Logging query: success=%s, retries=%d, latency=%.0fms",
        success, retry_count, latency_ms,
    )

    try:
        pool = await get_pool()
        await pool.execute(
            """
            INSERT INTO query_logs
                (user_question, generated_sql, final_sql, result_rows,
                 error_msg, retries, latency_ms, success, trace_data)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            user_question,
            generated_sql,
            final_sql,
            len(result_data),
            error_msg,
            retry_count,
            latency_ms,
            success,
            json.dumps(trace_steps, default=str),
        )
        logger.info("Query log inserted successfully")

        trace_steps.append({
            "node": "query_logger",
            "status": "success",
            "latency_ms": round(latency_ms, 1),
        })

    except Exception as e:
        logger.error("Failed to log query: %s", e)
        trace_steps.append({
            "node": "query_logger",
            "status": "error",
            "error": str(e),
        })

    return {
        "latency_ms": latency_ms,
        "trace_steps": trace_steps,
    }
