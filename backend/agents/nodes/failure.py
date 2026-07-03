import logging
from typing import Dict, Any

from agents.state import QueryState

logger = logging.getLogger("querymind.agents.nodes.failure")

async def failure_handler(state: QueryState) -> Dict[str, Any]:
    """
    Node 6: Terminal node invoked when all retry attempts are exhausted.
    """
    retry_count = state.get("retry_count", 0)
    error_msg = state.get("error_message", "Unknown error")
    question = state.get("user_question", "")
    last_sql = state.get("generated_sql", "")
    trace_steps = list(state.get("trace_steps", []))

    logger.warning(
        "Failure handler triggered after %d attempts for: %s",
        retry_count, question,
    )

    failure_message = (
        f"I was unable to generate a valid SQL query for your question "
        f"after {retry_count} attempt(s).\n\n"
        f"Last error: {error_msg}\n"
    )
    if last_sql:
        failure_message += f"Last attempted SQL: {last_sql}\n"

    failure_message += (
        "\nPlease try rephrasing your question or being more specific "
        "about which tables and columns you are interested in."
    )

    trace_steps.append({
        "node": "failure_handler",
        "status": "terminal",
        "retry_count": retry_count,
        "last_error": error_msg,
    })

    return {
        "success": False,
        "final_answer": failure_message,
        "trace_steps": trace_steps,
    }
