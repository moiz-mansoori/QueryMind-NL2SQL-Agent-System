import json
import logging
from typing import Dict, Any

from agents.state import QueryState
from config import GROQ_MODEL
from agents.prompts import FORMATTER_SYSTEM_PROMPT, get_formatter_user_prompt
from agents.nodes.utils import get_groq_client

logger = logging.getLogger("querymind.agents.nodes.formatter")

async def result_formatter(state: QueryState) -> Dict[str, Any]:
    """
    Node 7: Formats the SQL query results into a natural language answer.
    """
    question = state.get("user_question", "")
    result_data = state.get("result_data", [])
    sql = state.get("generated_sql", "")
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Formatting results for: %s (%d rows)", question, len(result_data))

    results_preview = []
    for row in result_data[:10]:
        clean_row = {}
        for k, v in row.items():
            val = str(v)
            if len(val) > 100:
                val = val[:97] + "..."
            clean_row[k] = val
        results_preview.append(clean_row)

    results_text = json.dumps(results_preview, indent=2, default=str)
    
    if len(result_data) > 10:
        results_text += f"\n... and {len(result_data) - 10} more rows"

    try:
        client = get_groq_client()
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": FORMATTER_SYSTEM_PROMPT},
                {"role": "user", "content": get_formatter_user_prompt(question, results_text)},
            ],
            temperature=0.3,
            max_tokens=512,
        )

        answer = response.choices[0].message.content or "No answer generated."
        logger.info("Formatted answer: %s", answer[:100])

        trace_steps.append({
            "node": "result_formatter",
            "status": "success",
            "model": GROQ_MODEL,
        })

        return {
            "final_answer": answer,
            "final_sql": sql,
            "success": True,
            "trace_steps": trace_steps,
        }

    except Exception as e:
        logger.error("Result formatting failed: %s", e)
        trace_steps.append({
            "node": "result_formatter",
            "status": "error",
            "error": str(e),
        })

        fallback_answer = (
            f"Query returned {len(result_data)} row(s). "
            f"Here are the raw results (formatting failed: {str(e)}):\n"
            f"{results_text}"
        )

        return {
            "final_answer": fallback_answer,
            "final_sql": sql,
            "success": True,
            "trace_steps": trace_steps,
        }
