import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from agents.nodes import (
    failure_handler,
    result_formatter,
    schema_retriever,
    sql_executor,
    sql_corrector,
    sql_validator,
    query_logger,
)


@pytest.fixture
def base_state() -> Dict[str, Any]:
    return {
        "user_question": "What is the total revenue?",
        "generated_sql": "SELECT revenue FROM unknown_table",
        "error_message": "Validation failed: unknown table referenced",
        "retry_count": 3,
        "result_data": [{"revenue": 50000}],
        "trace_steps": [],
        "start_time": 0,
        "success": False,
        "final_sql": "",
        "final_answer": "",
        "retrieved_schema": {},
    }


# ── failure_handler ─────────────────────────────────────

@pytest.mark.asyncio
async def test_failure_handler(base_state):
    """Test the failure handler formatting after max retries."""
    result = await failure_handler(base_state)

    assert result["success"] is False
    assert "unable to generate a valid SQL query" in result["final_answer"]
    assert "after 3 attempt(s)" in result["final_answer"]
    assert "last attempted sql" in result["final_answer"].lower()

    # Assert trace was appended
    assert len(result["trace_steps"]) == 1
    assert result["trace_steps"][0]["node"] == "failure_handler"
    assert result["trace_steps"][0]["status"] == "terminal"
    assert result["trace_steps"][0]["retry_count"] == 3


@pytest.mark.asyncio
async def test_max_retries_triggers_failure_handler(base_state):
    """Verify failure_handler activates when retry_count = MAX_RETRIES."""
    base_state["retry_count"] = 3  # MAX_RETRIES default
    result = await failure_handler(base_state)

    assert result["success"] is False
    assert result["trace_steps"][0]["node"] == "failure_handler"
    assert result["trace_steps"][0]["status"] == "terminal"


# ── result_formatter ────────────────────────────────────

@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_result_formatter_success(mock_async_groq, base_state):
    """Test successful natural language formatting."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="The total revenue is $50,000."))
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_async_groq.return_value = mock_client

    result = await result_formatter(base_state)

    assert result["success"] is True
    assert result["final_answer"] == "The total revenue is $50,000."
    assert result["trace_steps"][0]["status"] == "success"


@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_result_formatter_fallback(mock_async_groq, base_state):
    """Test result formatter falls back to raw data if LLM fails."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("LLM Formatting Error"))
    mock_async_groq.return_value = mock_client

    result = await result_formatter(base_state)

    # State still marked success because the core execution was successful
    assert result["success"] is True
    assert "Query returned 1 row(s)" in result["final_answer"]
    assert "revenue" in result["final_answer"]
    assert result["trace_steps"][0]["status"] == "error"


# ── schema_retriever ────────────────────────────────────

@pytest.mark.asyncio
@patch("agents.nodes.get_pool")
@patch("agents.nodes.get_embed_model")
async def test_schema_retriever_returns_schema(mock_embed, mock_pool, base_state):
    """Mock pgvector search, verify schema_retriever returns retrieved_schema."""
    import numpy as np

    # Mock the embedding model
    mock_model = MagicMock()
    mock_model.encode.return_value = np.zeros(384)
    mock_embed.return_value = mock_model

    # Mock the database pool and query result
    mock_row1 = {"table_name": "olist_orders", "column_name": "order_id", "description": "PK"}
    mock_row2 = {"table_name": "olist_orders", "column_name": "order_status", "description": "Status"}
    mock_pool_obj = MagicMock()
    mock_pool_obj.fetch = AsyncMock(return_value=[mock_row1, mock_row2])
    mock_pool.return_value = mock_pool_obj

    result = await schema_retriever(base_state)

    assert "olist_orders" in result["retrieved_schema"]
    assert len(result["retrieved_schema"]["olist_orders"]) == 2
    assert result["trace_steps"][0]["node"] == "schema_retriever"
    assert result["trace_steps"][0]["status"] == "success"


# ── sql_executor ────────────────────────────────────────

@pytest.mark.asyncio
@patch("agents.nodes.get_pool")
async def test_sql_executor_returns_results(mock_pool, base_state):
    """Mock asyncpg, verify sql_executor populates result_data on success."""
    base_state["generated_sql"] = "SELECT COUNT(*) AS cnt FROM olist_customers"

    mock_row = MagicMock()
    mock_row.__iter__ = MagicMock(return_value=iter([("cnt", 99393)]))
    mock_row.items = MagicMock(return_value=[("cnt", 99393)])
    mock_row.__getitem__ = MagicMock(side_effect=lambda k: 99393 if k == "cnt" else None)
    mock_row.keys = MagicMock(return_value=["cnt"])

    # asyncpg Record acts like a dict
    mock_pool_obj = MagicMock()
    mock_pool_obj.fetch = AsyncMock(return_value=[{"cnt": 99393}])
    mock_pool.return_value = mock_pool_obj

    result = await sql_executor(base_state)

    assert result["success"] is True
    assert len(result["result_data"]) == 1
    assert result["result_data"][0]["cnt"] == 99393
    assert result["trace_steps"][0]["node"] == "sql_executor"
    assert result["trace_steps"][0]["status"] == "success"


@pytest.mark.asyncio
@patch("agents.nodes.get_pool")
async def test_sql_executor_sets_error_on_failure(mock_pool, base_state):
    """Mock asyncpg to raise an error, verify executor captures it."""
    base_state["generated_sql"] = "SELECT * FROM olist_customers"

    mock_pool_obj = MagicMock()
    mock_pool_obj.fetch = AsyncMock(side_effect=Exception('relation "olist_customers" does not exist'))
    mock_pool.return_value = mock_pool_obj

    result = await sql_executor(base_state)

    assert result["success"] is False
    assert "does not exist" in result["error_message"]
    assert result["trace_steps"][0]["status"] == "error"


# ── sql_corrector ───────────────────────────────────────

@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_retry_count_increments(mock_async_groq, base_state):
    """Verify sql_corrector increments retry_count each time it fires."""
    base_state["retry_count"] = 1

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="SELECT COUNT(*) FROM olist_orders"))
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_async_groq.return_value = mock_client

    result = await sql_corrector(base_state)

    assert result["retry_count"] == 2  # was 1, now incremented
    assert result["trace_steps"][0]["node"] == "sql_corrector"
    assert result["trace_steps"][0]["status"] == "success"


# ── query_logger ────────────────────────────────────────

@pytest.mark.asyncio
@patch("agents.nodes.get_pool")
async def test_query_logger_inserts_row(mock_pool, base_state):
    """Mock asyncpg, verify query_logger calls INSERT."""
    import time
    base_state["start_time"] = time.time() - 2  # simulate 2s ago

    mock_pool_obj = MagicMock()
    mock_pool_obj.execute = AsyncMock(return_value=None)
    mock_pool.return_value = mock_pool_obj

    result = await query_logger(base_state)

    # Verify execute was called (INSERT INTO query_logs ...)
    mock_pool_obj.execute.assert_called_once()
    call_args = mock_pool_obj.execute.call_args
    assert "INSERT INTO query_logs" in call_args[0][0]

    assert result["latency_ms"] > 0
    assert result["trace_steps"][0]["node"] == "query_logger"
    assert result["trace_steps"][0]["status"] == "success"


# ── trace_steps populated ──────────────────────────────

@pytest.mark.asyncio
async def test_trace_steps_populated():
    """Verify trace_steps grows as nodes execute (using validator as example)."""
    state = {
        "generated_sql": "SELECT COUNT(*) FROM olist_customers",
        "trace_steps": [
            {"node": "schema_retriever", "status": "success"},
            {"node": "sql_generator", "status": "success"},
        ],
    }

    result = await sql_validator(state)

    # Should now have 3 steps (2 prior + 1 from validator)
    assert len(result["trace_steps"]) == 3
    assert result["trace_steps"][2]["node"] == "sql_validator"
