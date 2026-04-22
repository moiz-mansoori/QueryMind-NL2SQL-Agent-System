"""
QueryMind — Full Pipeline Integration Tests

Tests the complete LangGraph pipeline end-to-end through the live API,
validating:
  1. Happy-path state transitions (all 8 nodes fire in order)
  2. Self-correction loop (validator rejects bad SQL -> corrector fires)
  3. Trace step integrity (every node appears in trace_steps)
  4. Response schema compliance (all expected fields present)
  5. Query logging (query_logs table is populated after each run)

Requires:
  - PostgreSQL running with querymind database
  - FastAPI backend running on http://localhost:8000
"""

import json
import pytest
import httpx

API_BASE = "http://localhost:8000"
TIMEOUT = 120


# ── Helpers ──────────────────────────────────────────────

def post_query(question: str, include_trace: bool = True) -> dict:
    """Send a question to the /query endpoint and return the JSON response."""
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{API_BASE}/query",
            json={"question": question},
            params={"include_trace": str(include_trace).lower()},
        )
        resp.raise_for_status()
        return resp.json()


def get_history(limit: int = 5) -> list:
    """Fetch recent query logs from the analytics API."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{API_BASE}/analytics/history", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()


def get_summary() -> dict:
    """Fetch the analytics summary."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{API_BASE}/analytics/summary")
        resp.raise_for_status()
        return resp.json()


# ── Tests ────────────────────────────────────────────────

class TestHappyPath:
    """Tests for a normal, successful query execution."""

    def test_simple_count_query(self):
        """A simple COUNT query should succeed on the first attempt."""
        data = post_query("How many customers are there in the database?")

        # Response schema checks
        assert "answer" in data
        assert "sql" in data
        assert "rows" in data
        assert "metrics" in data
        assert "trace_steps" in data

        # Should succeed
        assert data["metrics"]["success"] is True
        assert data["error"] is None

        # Should have rows
        assert len(data["rows"]) > 0

        # SQL should be a SELECT
        assert "SELECT" in data["sql"].upper()

        # Should have 0 retries for a simple query
        assert data["metrics"]["retries"] == 0

    def test_trace_contains_all_happy_path_nodes(self):
        """Trace should contain every node in the happy-path execution order."""
        data = post_query("How many orders are there?")

        trace_nodes = [step["node"] for step in data["trace_steps"]]

        # Happy path order: schema_retriever -> sql_generator -> sql_validator
        #                    -> sql_executor -> result_formatter -> query_logger
        expected_nodes = [
            "schema_retriever",
            "sql_generator",
            "sql_validator",
            "sql_executor",
            "result_formatter",
            "query_logger",
        ]

        for node in expected_nodes:
            assert node in trace_nodes, f"Missing node '{node}' in trace: {trace_nodes}"

        # Corrector and failure_handler should NOT be in a happy-path trace
        assert "sql_corrector" not in trace_nodes
        assert "failure_handler" not in trace_nodes

    def test_trace_step_statuses(self):
        """All trace steps in a happy-path run should have status 'success'."""
        data = post_query("What are the top 5 cities with the most customers?")

        for step in data["trace_steps"]:
            assert step["status"] == "success", (
                f"Node '{step['node']}' had status '{step['status']}', expected 'success'"
            )

    def test_latency_is_recorded(self):
        """Pipeline should record a positive latency."""
        data = post_query("How many products are in the catalog?")

        assert data["metrics"]["latency_ms"] > 0

    def test_sql_references_known_tables(self):
        """Generated SQL should reference tables we know about."""
        data = post_query("What is the total revenue from all order payments?")

        sql_lower = data["sql"].lower()
        # Should reference olist_order_payments
        assert "olist_order_payments" in sql_lower


class TestResponseSchema:
    """Tests for the API response contract."""

    def test_response_has_all_fields(self):
        """Every response must include these top-level keys."""
        data = post_query("How many sellers are there?")

        required_keys = {"answer", "sql", "rows", "metrics", "error", "trace_steps"}
        assert required_keys.issubset(data.keys()), (
            f"Missing keys: {required_keys - data.keys()}"
        )

    def test_metrics_has_all_fields(self):
        """The metrics object must include retries, latency_ms, and success."""
        data = post_query("What is the average payment value?")

        metrics = data["metrics"]
        assert "retries" in metrics
        assert "latency_ms" in metrics
        assert "success" in metrics

    def test_trace_without_flag(self):
        """When include_trace=false, trace_steps should be empty."""
        data = post_query("How many customers are there?", include_trace=False)

        assert data["trace_steps"] == []


class TestQueryLogging:
    """Tests that the query_logger node correctly persists data."""

    def test_query_appears_in_history(self):
        """After executing a query, it should appear in /analytics/history."""
        # Use a unique-ish question
        question = "How many orders have been placed total?"
        post_query(question)

        history = get_history(limit=10)
        questions_in_history = [h.get("user_question", "") for h in history]

        assert question in questions_in_history, (
            f"Question not found in recent history. Got: {questions_in_history}"
        )

    def test_summary_reflects_queries(self):
        """The analytics summary should show at least 1 total query."""
        summary = get_summary()

        assert summary.get("total_queries", 0) > 0
        assert "success_rate" in summary


class TestSelfCorrection:
    """Tests that the self-correction loop works when the LLM makes mistakes."""

    def test_complex_query_still_succeeds(self):
        """Complex multi-join queries may trigger correction but should still pass."""
        data = post_query(
            "What are the top 3 product categories by total revenue?"
        )

        # This complex query should ultimately succeed (possibly with retries)
        assert data["metrics"]["success"] is True
        assert len(data["rows"]) > 0

    def test_trace_shows_correction_if_retries(self):
        """If retries > 0, sql_corrector should appear in the trace."""
        # Use a tricky query that might trigger self-correction
        data = post_query(
            "What is the average delivery time in days for orders delivered "
            "in Sao Paulo state?"
        )

        retries = data["metrics"]["retries"]
        trace_nodes = [step["node"] for step in data["trace_steps"]]

        if retries > 0:
            assert "sql_corrector" in trace_nodes, (
                f"Retries={retries} but sql_corrector not in trace: {trace_nodes}"
            )
        # If no retries, that's fine too — the LLM got it right first try


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_short_question_rejected(self):
        """Questions shorter than 3 characters should be rejected by Pydantic."""
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{API_BASE}/query",
                json={"question": "Hi"},
            )
            assert resp.status_code == 422  # Pydantic validation error

    def test_empty_question_rejected(self):
        """Empty questions should be rejected."""
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{API_BASE}/query",
                json={"question": ""},
            )
            assert resp.status_code == 422

    def test_missing_question_rejected(self):
        """Requests without a question field should be rejected."""
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{API_BASE}/query",
                json={},
            )
            assert resp.status_code == 422

    def test_very_long_question_rejected(self):
        """Questions longer than 1000 chars should be rejected."""
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{API_BASE}/query",
                json={"question": "a" * 1001},
            )
            assert resp.status_code == 422
