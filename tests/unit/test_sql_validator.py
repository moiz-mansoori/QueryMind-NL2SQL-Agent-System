import pytest
from typing import Dict, Any

from agents.nodes import sql_validator

@pytest.fixture
def base_state() -> Dict[str, Any]:
    return {
        "user_question": "Test question",
        "generated_sql": "",
        "trace_steps": []
    }

@pytest.mark.asyncio
async def test_valid_select_query(base_state):
    """Test that a valid SELECT query passes validation."""
    base_state["generated_sql"] = "SELECT COUNT(*) FROM olist_customers"
    result = await sql_validator(base_state)
    
    assert result.get("error_message") is None
    assert len(result["trace_steps"]) == 1
    assert result["trace_steps"][0]["status"] == "success"
    assert "olist_customers" in result["trace_steps"][0]["referenced_tables"]


@pytest.mark.asyncio
async def test_empty_sql_query(base_state):
    """Test that empty SQL is caught."""
    base_state["generated_sql"] = "   "
    result = await sql_validator(base_state)
    
    assert "empty" in result.get("error_message", "").lower()
    assert result["trace_steps"][0]["status"] == "error"


@pytest.mark.asyncio
async def test_syntax_error(base_state):
    """Test that invalid SQL syntax is caught by sqlglot."""
    base_state["generated_sql"] = "SELECT FROM WHERE"
    result = await sql_validator(base_state)
    
    assert "syntax error" in result.get("error_message", "").lower()
    assert result["trace_steps"][0]["status"] == "error"


@pytest.mark.asyncio
@pytest.mark.parametrize("dangerous_sql", [
    "DROP TABLE olist_customers",
    "DELETE FROM olist_orders",
    "TRUNCATE olist_products",
    "ALTER TABLE olist_sellers ADD COLUMN test INT",
    "UPDATE olist_customers SET customer_city = 'test'",
    "INSERT INTO olist_customers (customer_id) VALUES ('123')"
])
async def test_dangerous_keywords(base_state, dangerous_sql):
    """Test that DDL and DML operations are rejected."""
    base_state["generated_sql"] = dangerous_sql
    result = await sql_validator(base_state)
    
    assert "dangerous keyword" in result.get("error_message", "").lower()
    assert result["trace_steps"][0]["status"] == "error"


@pytest.mark.asyncio
async def test_unknown_table(base_state):
    """Test that queries referencing tables outside KNOWN_TABLES are rejected."""
    base_state["generated_sql"] = "SELECT * FROM secret_table"
    result = await sql_validator(base_state)
    
    assert "unknown table" in result.get("error_message", "").lower()
    assert "secret_table" in result.get("error_message", "").lower()
    assert result["trace_steps"][0]["status"] == "error"


@pytest.mark.asyncio
async def test_missing_where_clause_does_not_block(base_state):
    """SELECT without WHERE is perfectly valid and should pass."""
    base_state["generated_sql"] = "SELECT customer_id FROM olist_customers"
    result = await sql_validator(base_state)

    assert result.get("error_message") is None
    assert result["trace_steps"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_complex_join_query_passes(base_state):
    """Multi-table JOIN should validate successfully."""
    base_state["generated_sql"] = (
        "SELECT c.customer_id, o.order_id "
        "FROM olist_customers c "
        "JOIN olist_orders o ON c.customer_id = o.customer_id "
        "JOIN olist_order_items oi ON o.order_id = oi.order_id"
    )
    result = await sql_validator(base_state)

    assert result.get("error_message") is None
    assert result["trace_steps"][0]["status"] == "success"
    tables = result["trace_steps"][0]["referenced_tables"]
    assert "olist_customers" in tables
    assert "olist_orders" in tables
    assert "olist_order_items" in tables


@pytest.mark.asyncio
async def test_subquery_passes(base_state):
    """Nested SELECT (subquery) should validate successfully."""
    base_state["generated_sql"] = (
        "SELECT customer_id FROM olist_customers "
        "WHERE customer_id IN (SELECT customer_id FROM olist_orders)"
    )
    result = await sql_validator(base_state)

    assert result.get("error_message") is None
    assert result["trace_steps"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_sql_with_aggregation_passes(base_state):
    """GROUP BY / HAVING should validate successfully."""
    base_state["generated_sql"] = (
        "SELECT customer_id, COUNT(*) AS order_count "
        "FROM olist_orders "
        "GROUP BY customer_id "
        "HAVING COUNT(*) > 5"
    )
    result = await sql_validator(base_state)

    assert result.get("error_message") is None
    assert result["trace_steps"][0]["status"] == "success"
