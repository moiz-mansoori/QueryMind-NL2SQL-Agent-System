"""
QueryMind Agent Nodes

Contains the individual functional nodes that make up the LangGraph pipeline.
Nodes implemented:
  - schema_retriever  : vector-search for relevant schema context
  - sql_generator     : LLM-powered SQL generation via Groq
  - sql_validator     : syntax + safety + table-existence checks
  - sql_executor      : execute validated SQL against PostgreSQL
  - sql_corrector     : LLM-powered SQL correction on failure
  - failure_handler   : graceful termination after max retries
  - result_formatter  : LLM-powered natural language answer
  - query_logger      : persist execution trace to query_logs
"""

import json
import re
import time
import logging
from typing import Dict, Any

import sqlglot
from groq import AsyncGroq

from sentence_transformers import SentenceTransformer

from db.connection import get_pool
from agents.state import QueryState
from config import EMBED_MODEL, GROQ_API_KEY, GROQ_MODEL, KNOWN_TABLES, RESULT_LIMIT, MAX_RETRIES

logger = logging.getLogger("querymind.agents.nodes")

# Global Model Cache
_embed_model = None

def get_embed_model() -> SentenceTransformer:
    """Lazy load the sentence-transformers model to save memory."""
    global _embed_model
    if _embed_model is None:
        logger.info("Loading embedding model %s ...", EMBED_MODEL)
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


async def schema_retriever(state: QueryState) -> Dict[str, Any]:
    """
    Node 1: Retrieves relevant database schema definitions using vector search.
    
    Embeds the user's natural language question and performs a cosine 
    similarity search against the schema_embeddings table via pgvector.
    
    Args:
        state: Current QueryState containing user_question.
        
    Returns:
        Dict: State updates including retrieved_schema and trace_steps.
    """
    question = state.get("user_question", "")
    trace_steps = state.get("trace_steps", [])
    
    logger.info("Retrieving schema for question: %s", question)
    
    try:
        # 1. Embed the question
        model = get_embed_model()
        # SentenceTransformer output is typically a numpy array of shape (dim,)
        # Convert it to a flat list for asyncpg / pgvector
        query_embedding = model.encode(question).tolist()
        
        # 2. Vector search in PostgreSQL
        pool = await get_pool()
        
        # We use <-> for L2 distance (cosine similarity <=> is also fine, 
        # but <-> is heavily optimized by HNSW/IVFFlat indexes if we add them).
        # We'll use <=> (cosine distance) as specified in requirements.
        query = """
            SELECT table_name, column_name, description 
            FROM schema_embeddings
            ORDER BY embedding <=> $1::vector
            LIMIT 5
        """
        
        rows = await pool.fetch(query, query_embedding)
        
        # 3. Format the retrieved schema context
        schema_context = {}
        retrieved_items = []
        
        for row in rows:
            t_name = row["table_name"]
            c_name = row["column_name"]
            desc = row["description"]
            
            if t_name not in schema_context:
                schema_context[t_name] = []
            
            item = {"column": c_name, "description": desc}
            schema_context[t_name].append(item)
            retrieved_items.append(f"{t_name}.{c_name}" if c_name else f"{t_name} (table)")
            
        logger.info("Retrieved schema logic found: %s", ", ".join(retrieved_items))
        
        # 4. Update trace
        step = {
            "node": "schema_retriever",
            "status": "success",
            "retrieved_tables_count": len(schema_context),
            "retrieved_items": retrieved_items
        }
        trace_steps.append(step)
        
        return {
            "retrieved_schema": schema_context,
            "trace_steps": trace_steps
        }
        
    except Exception as e:
        logger.error("schema_retriever failed: %s", e)
        # Even if it fails, we return an empty schema so the next node can at least try
        # or fail gracefully.
        step = {
            "node": "schema_retriever",
            "status": "error",
            "error": str(e)
        }
        trace_steps.append(step)
        return {
            "retrieved_schema": {},
            "trace_steps": trace_steps,
            "error_message": f"Schema retrieval failed: {str(e)}"
        }


def _format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    """
    Convert the retrieved_schema dict into a human-readable string
    suitable for inclusion in an LLM prompt.

    Args:
        schema: Dict mapping table names to lists of column descriptors.

    Returns:
        A formatted multi-line string describing the available schema.
    """
    if not schema:
        return "No schema information available."

    lines = []
    for table_name, columns in schema.items():
        lines.append(f"Table: {table_name}")
        for col in columns:
            col_name = col.get("column", "")
            desc = col.get("description", "")
            if col_name:
                lines.append(f"  - {col_name}: {desc}")
            else:
                # Table-level description (no specific column)
                lines.append(f"  (table description): {desc}")
        lines.append("")  # blank separator between tables
    return "\n".join(lines)


def _clean_sql_response(raw: str) -> str:
    """
    Strip markdown fences, backticks, and any non-SQL prose from the
    LLM's raw output so we get a clean SQL string.

    Args:
        raw: The raw text returned by the LLM.

    Returns:
        A cleaned SQL query string.
    """
    text = raw.strip()

    # Remove ```sql ... ``` or ``` ... ``` fenced blocks
    fenced = re.search(r"```(?:sql)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    # Remove inline backticks that sometimes wrap the whole query
    text = text.strip("`").strip()

    # If the model returned explanation before/after the SQL,
    # try to extract only the SQL statement(s).
    # A SQL statement typically starts with SELECT, WITH, INSERT, etc.
    sql_match = re.search(
        r"((?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|EXPLAIN)\b.+)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if sql_match:
        text = sql_match.group(1).strip()

    # Remove any trailing semicolons (asyncpg doesn't want them)
    text = text.rstrip(";")

    return text


async def sql_generator(state: QueryState) -> Dict[str, Any]:
    """
    Node 2: Generates a PostgreSQL SQL query from the user's question
    using the Groq LLM (llama-3.3-70b-versatile).

    Takes the retrieved_schema context from the previous node and builds
    a structured prompt that instructs the model to produce *only* a raw
    SQL query — no markdown, no explanation.

    Args:
        state: Current QueryState with user_question and retrieved_schema.

    Returns:
        Dict with generated_sql and updated trace_steps.
    """
    question = state.get("user_question", "")
    schema = state.get("retrieved_schema", {})
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Generating SQL for: %s", question)

    # Build the prompt
    schema_text = _format_schema_for_prompt(schema)

    system_prompt = (
        "You are a PostgreSQL SQL expert. Given the following database schema "
        "and a user question, generate a valid PostgreSQL SQL query.\n\n"
        "RULES:\n"
        "- Return ONLY the SQL query, nothing else\n"
        "- No markdown, no backticks, no explanation\n"
        "- Use only the tables and columns provided in the schema\n"
        "- Use PostgreSQL syntax\n"
        "- Always include reasonable column aliases for readability\n"
        "- If the question is ambiguous, make a reasonable assumption\n\n"
        "DATABASE SCHEMA:\n"
        f"{schema_text}"
    )

    user_prompt = f"Question: {question}"

    # Call Groq API
    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,       # deterministic output for SQL
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

# ------------------------------------------------------------------
# Dangerous SQL keywords that must never reach the executor
# ------------------------------------------------------------------
_DANGEROUS_KEYWORDS = {"DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT"}


async def sql_validator(state: QueryState) -> Dict[str, Any]:
    """
    Node 3: Validates the generated SQL before execution.

    Performs three layers of validation:
      1. **Syntax check** - parses the SQL via sqlglot; catches malformed queries.
      2. **Safety check** - rejects any query containing dangerous DDL/DML
         keywords (DROP, DELETE, TRUNCATE, ALTER, UPDATE, INSERT).
      3. **Table existence check** - extracts every table referenced in the
         query and verifies it exists in the project's KNOWN_TABLES set.

    If validation passes, ``error_message`` is cleared so the graph routes
    to the executor.  If it fails, ``error_message`` is populated so the
    graph can route to the corrector instead.

    Args:
        state: Current QueryState with generated_sql.

    Returns:
        Dict with error_message (None on success) and updated trace_steps.
    """
    sql = state.get("generated_sql", "")
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Validating SQL: %s", sql[:120])

    # Edge case: empty SQL
    if not sql.strip():
        error = "Validation failed: SQL query is empty."
        logger.warning(error)
        trace_steps.append({"node": "sql_validator", "status": "error", "error": error})
        return {"error_message": error, "trace_steps": trace_steps}

    # 1. Syntax check via sqlglot
    try:
        parsed = sqlglot.parse(sql, read="postgres")
        if not parsed or parsed[0] is None:
            raise sqlglot.errors.ParseError("sqlglot returned empty parse tree")
    except sqlglot.errors.ParseError as e:
        error = f"Validation failed: SQL syntax error - {e}"
        logger.warning(error)
        trace_steps.append({"node": "sql_validator", "status": "error", "error": error})
        return {"error_message": error, "trace_steps": trace_steps}

    # 2. Safety check - reject dangerous statements
    sql_upper = sql.upper()
    for keyword in _DANGEROUS_KEYWORDS:
        # Use word-boundary check so column names like "updated_at" don't
        # false-positive on "UPDATE".
        if re.search(rf"\b{keyword}\b", sql_upper):
            error = f"Validation failed: dangerous keyword '{keyword}' detected. Only SELECT queries are allowed."
            logger.warning(error)
            trace_steps.append({"node": "sql_validator", "status": "error", "error": error})
            return {"error_message": error, "trace_steps": trace_steps}

    # 3. Table existence check - extract all table names from the AST
    referenced_tables = set()
    for expression in parsed:
        if expression is None:
            continue
        for table in expression.find_all(sqlglot.exp.Table):
            table_name = table.name
            if table_name:
                referenced_tables.add(table_name.lower())

    known_lower = {t.lower() for t in KNOWN_TABLES}
    unknown_tables = referenced_tables - known_lower

    if unknown_tables:
        error = (
            f"Validation failed: unknown table(s) referenced: "
            f"{', '.join(sorted(unknown_tables))}. "
            f"Known tables: {', '.join(sorted(known_lower))}"
        )
        logger.warning(error)
        trace_steps.append({"node": "sql_validator", "status": "error", "error": error})
        return {"error_message": error, "trace_steps": trace_steps}

    # All checks passed
    logger.info("SQL validation passed (tables: %s)", ", ".join(sorted(referenced_tables)))
    trace_steps.append({
        "node": "sql_validator",
        "status": "success",
        "referenced_tables": sorted(referenced_tables),
    })

    return {
        "error_message": None,
        "trace_steps": trace_steps,
    }


async def sql_executor(state: QueryState) -> Dict[str, Any]:
    """
    Node 4: Executes the validated SQL query against PostgreSQL.

    Reads the SQL from ``generated_sql`` (or ``final_sql`` if a correction
    has overwritten it).  If the query lacks a LIMIT clause, one is
    automatically appended (capped at RESULT_LIMIT from config, default 500)
    to avoid accidentally pulling millions of rows.

    On success, rows are converted to a list of plain dicts and stored in
    ``result_data``.  On failure, the error is captured in ``error_message``
    and ``retry_count`` is incremented so the graph can route to the
    corrector node.

    Args:
        state: Current QueryState with generated_sql / final_sql.

    Returns:
        Dict with result_data, success flag, error_message, and trace_steps.
    """
    # Prefer final_sql (set by corrector) over generated_sql
    sql = state.get("final_sql") or state.get("generated_sql", "")
    trace_steps = list(state.get("trace_steps", []))
    retry_count = state.get("retry_count", 0)

    logger.info("Executing SQL: %s", sql[:120])

    # Auto-append LIMIT if missing
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql.rstrip().rstrip(';')} LIMIT {RESULT_LIMIT}"
        logger.info("Auto-appended LIMIT %d", RESULT_LIMIT)

    try:
        pool = await get_pool()
        rows = await pool.fetch(sql)

        # Convert asyncpg Record objects to plain dicts
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


async def sql_corrector(state: QueryState) -> Dict[str, Any]:
    """
    Node 5: Attempts to fix a failed SQL query using the Groq LLM.

    When the validator or executor reports an error, this node feeds the
    original question, the broken SQL, the error message, and the retrieved
    schema back to the LLM with an explicit instruction to produce a
    corrected query.

    The corrected SQL replaces ``generated_sql`` so the graph can loop
    back through the validator -> executor path.  ``retry_count`` is
    incremented each time this node fires.

    Args:
        state: Current QueryState with generated_sql, error_message,
               user_question, and retrieved_schema.

    Returns:
        Dict with corrected generated_sql, incremented retry_count,
        cleared error_message, and updated trace_steps.
    """
    question = state.get("user_question", "")
    failed_sql = state.get("generated_sql", "")
    error_msg = state.get("error_message", "")
    schema = state.get("retrieved_schema", {})
    retry_count = state.get("retry_count", 0)
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Correcting SQL (attempt %d): %s", retry_count + 1, failed_sql[:80])

    schema_text = _format_schema_for_prompt(schema)

    correction_prompt = (
        "The following SQL query failed with an error.\n\n"
        f"Original question: {question}\n"
        f"Failed SQL: {failed_sql}\n"
        f"Error: {error_msg}\n\n"
        f"Database schema:\n{schema_text}\n\n"
        "RULES:\n"
        "- Generate a corrected PostgreSQL SQL query\n"
        "- Return ONLY the SQL query, nothing else\n"
        "- No markdown, no backticks, no explanation\n"
        "- Use only the tables and columns provided in the schema\n"
        "- Fix the specific error mentioned above\n"
    )

    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a PostgreSQL SQL expert. Fix the broken SQL query."},
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


async def failure_handler(state: QueryState) -> Dict[str, Any]:
    """
    Node 6: Terminal node invoked when all retry attempts are exhausted.

    Builds a user-friendly failure message explaining that the system
    was unable to generate a valid SQL query after ``MAX_RETRIES``
    attempts, and includes the last error for debugging context.

    Args:
        state: Current QueryState after all retries have been used.

    Returns:
        Dict with success=False, final_answer containing the failure
        message, and updated trace_steps.
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


async def result_formatter(state: QueryState) -> Dict[str, Any]:
    """
    Node 7: Formats the SQL query results into a natural language answer.

    Calls the Groq LLM with the original user question and a summary of
    the result data, asking it to produce a concise 2-3 sentence answer
    that a non-technical user can understand.

    Args:
        state: Current QueryState with user_question, result_data,
               and generated_sql.

    Returns:
        Dict with final_answer, final_sql, success=True, and trace_steps.
    """
    question = state.get("user_question", "")
    result_data = state.get("result_data", [])
    sql = state.get("generated_sql", "")
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Formatting results for: %s (%d rows)", question, len(result_data))

    # Build a concise summary of the results (limit to first 20 rows to
    # avoid blowing up the prompt)
    results_preview = result_data[:20]
    results_text = json.dumps(results_preview, indent=2, default=str)
    if len(result_data) > 20:
        results_text += f"\n... and {len(result_data) - 20} more rows"

    try:
        client = AsyncGroq(api_key=GROQ_API_KEY)
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful data analyst. Given the user's question "
                        "and the SQL query results, provide a brief, clear natural "
                        "language answer in 2-3 sentences. Be specific with numbers "
                        "and data points. Do not mention SQL or technical details."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\n"
                        f"Query Results:\n{results_text}"
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=512,
        )

        answer = response.choices[0].message.content or "No answer generated."
        logger.info("Formatted answer: %s", answer[:100])

        trace_steps.append({
            "node": "result_formatter",
            "status": "success",
            "answer_preview": answer[:100],
        })

        return {
            "final_answer": answer,
            "final_sql": sql,
            "success": True,
            "trace_steps": trace_steps,
        }

    except Exception as e:
        # If formatting fails, fall back to a raw data summary
        logger.error("result_formatter failed: %s", e)
        fallback = f"Query returned {len(result_data)} row(s). Raw results: {results_text[:200]}"

        trace_steps.append({
            "node": "result_formatter",
            "status": "error",
            "error": str(e),
        })

        return {
            "final_answer": fallback,
            "final_sql": sql,
            "success": True,  # query itself succeeded, just formatting failed
            "trace_steps": trace_steps,
        }


async def query_logger(state: QueryState) -> Dict[str, Any]:
    """
    Node 8: Persists the full execution trace into the query_logs table.

    Calculates the total latency from ``start_time``, serializes all
    trace steps to JSON, and inserts a row into ``query_logs`` for
    analytics and debugging.

    This is always the **last node** in the graph — it runs after both
    success (result_formatter) and failure (failure_handler) paths.

    Args:
        state: Final QueryState with all fields populated.

    Returns:
        Dict with latency_ms and updated trace_steps.
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
