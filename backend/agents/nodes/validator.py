import re
import logging
from typing import Dict, Any

import sqlglot
from db.connection import get_db_tables
from agents.state import QueryState
from config import FALLBACK_KNOWN_TABLES

logger = logging.getLogger("querymind.agents.nodes.validator")

_DANGEROUS_KEYWORDS = {"DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT"}

async def sql_validator(state: QueryState) -> Dict[str, Any]:
    """
    Node 3: Validates the generated SQL before execution.
    """
    sql = state.get("generated_sql", "")
    trace_steps = list(state.get("trace_steps", []))

    logger.info("Validating SQL: %s", sql[:120])

    if not sql.strip():
        error = "Validation failed: SQL query is empty."
        logger.warning(error)
        trace_steps.append({"node": "sql_validator", "status": "error", "error": error})
        return {"error_message": error, "trace_steps": trace_steps}

    try:
        parsed = sqlglot.parse(sql, read="postgres")
        if not parsed or parsed[0] is None:
            raise sqlglot.errors.ParseError("sqlglot returned empty parse tree")
    except sqlglot.errors.ParseError as e:
        error = f"Validation failed: SQL syntax error - {e}"
        logger.warning(error)
        trace_steps.append({"node": "sql_validator", "status": "error", "error": error})
        return {"error_message": error, "trace_steps": trace_steps}

    sql_upper = sql.upper()
    for keyword in _DANGEROUS_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_upper):
            error = f"Validation failed: dangerous keyword '{keyword}' detected. Only SELECT queries are allowed."
            logger.warning(error)
            trace_steps.append({"node": "sql_validator", "status": "error", "error": error})
            return {"error_message": error, "trace_steps": trace_steps}

    referenced_tables = set()
    for expression in parsed:
        if expression is None:
            continue
        for table in expression.find_all(sqlglot.exp.Table):
            table_name = table.name
            if table_name:
                referenced_tables.add(table_name.lower())

    db_tables = await get_db_tables()
    if not db_tables:
        logger.warning("Dynamic schema discovery failed, using fallback tables")
        db_tables = FALLBACK_KNOWN_TABLES

    known_lower = {t.lower() for t in db_tables}
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
