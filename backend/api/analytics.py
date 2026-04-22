"""
QueryMind Analytics API Router

Provides read-only endpoints for querying pipeline execution history,
performance metrics, and failure analysis from the query_logs table.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from db.connection import get_pool

logger = logging.getLogger("querymind.api.analytics")

router = APIRouter(tags=["analytics"])


# ── Response Models ──────────────────────────────────────

class SummaryResponse(BaseModel):
    """Aggregate metrics across all logged queries."""
    total_queries: int = 0
    success_rate: float = 0.0
    avg_retries: float = 0.0
    avg_latency_ms: float = 0.0


class QueryLogRow(BaseModel):
    """Single row from the query_logs table."""
    id: int
    user_question: str
    generated_sql: Optional[str] = None
    final_sql: Optional[str] = None
    result_rows: int = 0
    error_msg: Optional[str] = None
    retries: int = 0
    latency_ms: float = 0.0
    success: bool = False
    trace_data: Optional[Any] = None
    created_at: Optional[datetime] = None


class DailyStats(BaseModel):
    """Per-day aggregated statistics for chart rendering."""
    date: str
    count: int = 0
    success: int = 0
    failure: int = 0


# ── Helper ───────────────────────────────────────────────

def _row_to_dict(row) -> Dict[str, Any]:
    """Convert an asyncpg Record to a JSON-safe dict."""
    d = dict(row)
    # Make datetime serializable
    if "created_at" in d and d["created_at"] is not None:
        d["created_at"] = d["created_at"].isoformat()
    return d


# ── Routes ───────────────────────────────────────────────

@router.get("/summary", response_model=SummaryResponse)
async def analytics_summary() -> SummaryResponse:
    """
    Return aggregate metrics: total queries, success rate,
    average retries, and average latency.
    """
    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT
            COUNT(*)                          AS total,
            COALESCE(AVG(success::int), 0)    AS success_rate,
            COALESCE(AVG(retries), 0)         AS avg_retries,
            COALESCE(AVG(latency_ms), 0)      AS avg_latency
        FROM query_logs
    """)

    return SummaryResponse(
        total_queries=row["total"],
        success_rate=round(float(row["success_rate"]) * 100, 2),
        avg_retries=round(float(row["avg_retries"]), 2),
        avg_latency_ms=round(float(row["avg_latency"]), 2),
    )


@router.get("/history", response_model=List[QueryLogRow])
async def analytics_history(
    limit: int = Query(default=50, ge=1, le=500, description="Max rows to return"),
) -> List[Dict[str, Any]]:
    """
    Return recent query log entries ordered by newest first.
    """
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT id, user_question, generated_sql, final_sql,
               result_rows, error_msg, retries, latency_ms,
               success, trace_data, created_at
        FROM query_logs
        ORDER BY created_at DESC
        LIMIT $1
    """, limit)

    return [_row_to_dict(r) for r in rows]


@router.get("/failures", response_model=List[QueryLogRow])
async def analytics_failures(
    limit: int = Query(default=50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """
    Return failed queries (success = FALSE), ordered by newest first.
    """
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT id, user_question, generated_sql, final_sql,
               result_rows, error_msg, retries, latency_ms,
               success, trace_data, created_at
        FROM query_logs
        WHERE success = FALSE
        ORDER BY created_at DESC
        LIMIT $1
    """, limit)

    return [_row_to_dict(r) for r in rows]


@router.get("/slow-queries", response_model=List[QueryLogRow])
async def analytics_slow_queries(
    threshold_ms: float = Query(
        default=2000.0, ge=0, description="Latency threshold in milliseconds"
    ),
    limit: int = Query(default=50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """
    Return queries slower than the given threshold,
    ordered by slowest first.
    """
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT id, user_question, generated_sql, final_sql,
               result_rows, error_msg, retries, latency_ms,
               success, trace_data, created_at
        FROM query_logs
        WHERE latency_ms > $1
        ORDER BY latency_ms DESC
        LIMIT $2
    """, threshold_ms, limit)

    return [_row_to_dict(r) for r in rows]


@router.get("/trace/{query_id}", response_model=Dict[str, Any])
async def analytics_trace(query_id: int) -> Dict[str, Any]:
    """
    Return the full execution trace data for a specific query.
    """
    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT trace_data
        FROM query_logs
        WHERE id = $1
    """, query_id)

    if not row:
        raise HTTPException(status_code=404, detail="Query not found")

    return {"trace_data": json.loads(row["trace_data"]) if row["trace_data"] else []}


@router.get("/queries-per-day", response_model=List[DailyStats])
async def analytics_queries_per_day(
    days: int = Query(default=7, ge=1, le=30),
) -> List[Dict[str, Any]]:
    """
    Aggregate query_logs by date for chart rendering.
    """
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as count,
            SUM(success::int) as success,
            SUM((NOT success)::int) as failure
        FROM query_logs
        WHERE created_at >= (CURRENT_DATE - INTERVAL '1 day' * $1)
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at) ASC
    """, days)

    result = []
    for r in rows:
        result.append({
            "date": r["date"].isoformat() if r["date"] else "",
            "count": r["count"],
            "success": r["success"],
            "failure": r["failure"]
        })
    return result


class DailyStatsDetailed(BaseModel):
    """Per-day statistics with explicit field names for the daily-stats endpoint."""
    date: str
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0


@router.get("/daily-stats", response_model=List[DailyStatsDetailed])
async def analytics_daily_stats() -> List[Dict[str, Any]]:
    """
    Return queries grouped by day for the last 7 days.
    Returns date, total_count, success_count, failure_count.
    """
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT
            DATE(created_at)           AS date,
            COUNT(*)                   AS total_count,
            SUM(success::int)          AS success_count,
            SUM((NOT success)::int)    AS failure_count
        FROM query_logs
        WHERE created_at >= (CURRENT_DATE - INTERVAL '7 days')
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at) ASC
    """)

    return [
        {
            "date": r["date"].isoformat() if r["date"] else "",
            "total_count": r["total_count"],
            "success_count": r["success_count"],
            "failure_count": r["failure_count"],
        }
        for r in rows
    ]
