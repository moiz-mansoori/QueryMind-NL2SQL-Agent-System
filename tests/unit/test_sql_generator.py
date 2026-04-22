import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from agents.nodes import sql_generator

@pytest.fixture
def base_state() -> Dict[str, Any]:
    return {
        "user_question": "How many customers are there?",
        "retrieved_schema": {
            "olist_customers": [
                {"column": "customer_id", "description": "Unique identifier for customer"},
            ]
        },
        "trace_steps": []
    }

@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_sql_generator_success(mock_async_groq, base_state):
    """Test successful SQL generation with mocked Groq client."""
    # Setup mock response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="```sql\nSELECT COUNT(customer_id) FROM olist_customers;\n```"))
    ]
    # Configure the chained async mock
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_async_groq.return_value = mock_client
    
    result = await sql_generator(base_state)
    
    # Verify the generated SQL is cleaned of markdown and backticks
    assert "```" not in result["generated_sql"]
    assert result["generated_sql"] == "SELECT COUNT(customer_id) FROM olist_customers"
    assert "error_message" not in result
    assert result["trace_steps"][0]["status"] == "success"
    assert result["trace_steps"][0]["node"] == "sql_generator"

@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_sql_generator_api_failure(mock_async_groq, base_state):
    """Test SQL generation gracefully handles API failures."""
    # Setup mock to raise an exception
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API rate limit exceeded"))
    mock_async_groq.return_value = mock_client
    
    result = await sql_generator(base_state)
    
    assert result["generated_sql"] == ""
    assert "API rate limit exceeded" in result.get("error_message", "")
    assert result["trace_steps"][0]["status"] == "error"

@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_sql_generator_with_empty_schema(mock_async_groq, base_state):
    """Test SQL generation still functions without retrieved schema."""
    base_state["retrieved_schema"] = {}
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="SELECT * FROM my_table;"))
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_async_groq.return_value = mock_client
    
    result = await sql_generator(base_state)
    
    assert result["generated_sql"] == "SELECT * FROM my_table"
    assert result["trace_steps"][0]["status"] == "success"


@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_prompt_contains_schema_context(mock_async_groq, base_state):
    """Verify that the schema context is embedded in the system prompt sent to Groq."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="SELECT 1"))
    ]
    mock_create = AsyncMock(return_value=mock_response)
    mock_client.chat.completions.create = mock_create
    mock_async_groq.return_value = mock_client

    await sql_generator(base_state)

    # Inspect the messages kwarg passed to create()
    call_kwargs = mock_create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages") or call_kwargs[0][0] if call_kwargs[0] else None
    if messages is None:
        # Try positional
        messages = call_kwargs[1]["messages"]

    system_msg = messages[0]["content"]
    # Should contain the table name and column from retrieved_schema
    assert "olist_customers" in system_msg
    assert "customer_id" in system_msg


@pytest.mark.asyncio
@patch("agents.nodes.AsyncGroq")
async def test_prompt_contains_user_question(mock_async_groq, base_state):
    """Verify that the user's question appears in the user prompt sent to Groq."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="SELECT 1"))
    ]
    mock_create = AsyncMock(return_value=mock_response)
    mock_client.chat.completions.create = mock_create
    mock_async_groq.return_value = mock_client

    await sql_generator(base_state)

    call_kwargs = mock_create.call_args
    messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")

    user_msg = messages[1]["content"]
    assert "How many customers are there?" in user_msg
