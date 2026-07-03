import logging
from typing import Dict, Any

from agents.state import QueryState
from config import GROQ_MODEL
from agents.prompts import get_sql_corrector_user_prompt, CORRECTOR_SYSTEM_PROMPT
from agents.nodes.utils import get_groq_client, _format_schema_for_prompt, _clean_sql_response

logger = logging.getLogger("querymind.agents.nodes.corrector")

async def sql_corrector(state: QueryState) -> Dict[str, Any]:
    """
    Node 5: Attempts to fix a failed SQL query using the Groq LLM.
    """
    question = state.get("user_question", "")
    failed_sql = state.get("generated_sql", "")
    error_msg = state.get("error_message", "")
    schema = state.get("retrieved_schema", {})
    retry_count = state.get("retry_count", 0)
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Correcting SQL (attempt %d): %s", retry_count + 1, failed_sql[:80])

    schema_text = _format_schema_for_prompt(schema)
    correction_prompt = get_sql_corrector_user_prompt(question, failed_sql, error_msg, schema_text)

    try:
        client = get_groq_client()
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": CORRECTOR_SYSTEM_PROMPT},
                {"role": "user", "content": correction_prompt},
            ],
            temperature=0,
            max_tokens=1024,
        )

        raw_sql = response.choices[0].message.content or ""
        corrected_sql = _clean_sql_response(raw_sql)

        logger.info("Corrected SQL: %s", corrected_sql)

        trace_steps.append({
            "node": "sql_corrector",
            "status": "success",
            "attempt": retry_count + 1,
            "original_sql": failed_sql,
            "corrected_sql": corrected_sql,
            "error_fixed": error_msg,
        })

        return {
            "generated_sql": corrected_sql,
            "retry_count": retry_count + 1,
            "error_message": None,   # clear so validator gets a fresh shot
            "trace_steps": trace_steps,
        }

    except Exception as e:
        correction_error = f"SQL correction failed: {str(e)}"
        logger.error(correction_error)

        trace_steps.append({
            "node": "sql_corrector",
            "status": "error",
            "attempt": retry_count + 1,
            "error": str(e),
        })

        return {
            "retry_count": retry_count + 1,
            "error_message": correction_error,
            "trace_steps": trace_steps,
        }
