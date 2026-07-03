import logging
from typing import Dict, Any

from agents.state import QueryState
from config import GROQ_MODEL
from agents.prompts import get_sql_generator_system_prompt
from agents.nodes.utils import get_groq_client, _format_schema_for_prompt, _clean_sql_response

logger = logging.getLogger("querymind.agents.nodes.generator")

async def sql_generator(state: QueryState) -> Dict[str, Any]:
    """
    Node 2: Generates a PostgreSQL SQL query from the user's question
    using the Groq LLM.
    """
    question = state.get("user_question", "")
    schema = state.get("retrieved_schema", {})
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Generating SQL for: %s", question)

    schema_text = _format_schema_for_prompt(schema)
    system_prompt = get_sql_generator_system_prompt(schema_text)
    user_prompt = f"Question: {question}"

    try:
        client = get_groq_client()
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=1024,
        )

        raw_sql = response.choices[0].message.content or ""
        generated_sql = _clean_sql_response(raw_sql)

        logger.info("Generated SQL: %s", generated_sql)

        trace_steps.append({
            "node": "sql_generator",
            "status": "success",
            "generated_sql": generated_sql,
            "model": GROQ_MODEL,
        })

        return {
            "generated_sql": generated_sql,
            "trace_steps": trace_steps,
        }

    except Exception as e:
        error_msg = f"SQL generation failed: {str(e)}"
        logger.error(error_msg)

        trace_steps.append({
            "node": "sql_generator",
            "status": "error",
            "error": str(e),
        })

        return {
            "generated_sql": "",
            "error_message": error_msg,
            "trace_steps": trace_steps,
        }
