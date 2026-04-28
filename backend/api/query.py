"""
QueryMind Query API Router

Exposes the POST /query endpoint that accepts a natural language question,
invokes the LangGraph pipeline, and returns the structured result.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from agents.graph import run_query

logger = logging.getLogger("querymind.api.query")

router = APIRouter(tags=["query"])


# ── Request / Response Models ────────────────────────────

class QueryRequest(BaseModel):
    """Incoming query payload."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language question about the database.",
        examples=["How many customers are there?"],
    )


class QueryMetrics(BaseModel):
    """Execution metrics returned alongside the answer."""
    retries: int = 0
    latency_ms: float = 0.0
    success: bool = False


class QueryResponse(BaseModel):
    """Full response from the /query endpoint."""
    answer: str = Field("", description="Natural language summary of the results.")
    sql: str = Field("", description="Final SQL query that was executed.")
    rows: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Raw result rows from the database.",
    )
    metrics: QueryMetrics = Field(default_factory=QueryMetrics)
    error: Optional[str] = Field(None, description="Error message if the query failed.")
    trace_steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Step-by-step execution trace for replay (only when include_trace=true).",
    )


from utils.limiter import limiter

# ── Route ────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
async def execute_query(
    request: Request,
    payload: QueryRequest,
    include_trace: bool = Query(
        default=False,
        description="If true, include step-by-step trace_steps in the response.",
    ),
) -> QueryResponse:
    """
    Accept a natural language question, run it through the full
    LangGraph agent pipeline, and return the answer + metadata.

    - Validates the question via Pydantic.
    - Invokes `run_query()` from the compiled StateGraph.
    - Maps the final pipeline state into a clean API response.
    - Optionally includes trace_steps when `include_trace=true`.

    Raises:
        HTTPException 500: If the pipeline crashes unexpectedly.
    """
    question = payload.question.strip()
    logger.info("API /query received: %s", question[:120])

    try:
        state = await run_query(question)
    except Exception as exc:
        logger.error("Pipeline invocation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal pipeline error: {str(exc)}",
        )

    # ── Map pipeline state → API response ────────────────
    success = state.get("success", False)
    answer = state.get("final_answer", "")
    sql = state.get("final_sql") or state.get("generated_sql", "")
    rows = state.get("result_data", [])
    retries = state.get("retry_count", 0)
    latency = state.get("latency_ms", 0.0)
    error_msg = state.get("error_message") if not success else None
    trace = state.get("trace_steps", []) if include_trace else []

    return QueryResponse(
        answer=answer,
        sql=sql,
        rows=rows,
        metrics=QueryMetrics(
            retries=retries,
            latency_ms=round(latency, 2),
            success=success,
        ),
        error=error_msg,
        trace_steps=trace,
    )
