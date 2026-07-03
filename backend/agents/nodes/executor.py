import re
import logging
from typing import Dict, Any

from db.connection import get_pool
from agents.state import QueryState
from config import RESULT_LIMIT

logger = logging.getLogger("querymind.agents.nodes.executor")

async def sql_executor(state: QueryState) -> Dict[str, Any]:
    """
    Node 4: Executes the validated SQL query against PostgreSQL.
    """
    sql = state.get("final_sql") or state.get("generated_sql", "")
    trace_steps = list(state.get("trace_steps", []))
    retry_count = state.get("retry_count", 0)

    logger.info("Executing SQL: %s", sql[:120])

    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql.rstrip().rstrip(';')} LIMIT {RESULT_LIMIT}"
        logger.info("Auto-appended LIMIT %d", RESULT_LIMIT)

    try:
        pool = await get_pool()
        rows = await pool.fetch(sql)

        result_data = [dict(row) for row in rows]

        logger.info("Query returned %d rows", len(result_data))

        trace_steps.append({
            "node": "sql_executor",
            "status": "success",
            "row_count": len(result_data),
        })

        return {
            "result_data": result_data,
            "success": True,
            "error_message": None,
            "final_sql": sql,
            "trace_steps": trace_steps,
        }

    except Exception as e:
        error_msg = f"SQL execution failed: {str(e)}"
        logger.error(error_msg)

        trace_steps.append({
            "node": "sql_executor",
            "status": "error",
            "error": str(e),
        })

        return {
            "result_data": [],
            "success": False,
            "error_message": error_msg,
            "trace_steps": trace_steps,
        }
