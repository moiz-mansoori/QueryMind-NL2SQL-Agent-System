"""
QueryMind Agent State

Defines the state schema for the LangGraph workflow.
"""

from typing import TypedDict, List, Dict, Any, Optional

class QueryState(TypedDict):
    """
    State shared across all nodes in the LangGraph query execution pipeline.
    """
    # Inputs
    user_question: str
    
    # Retrieval Phase
    retrieved_schema: Dict[str, Any]
    
    # Generation & Correction Phase
    generated_sql: str
    final_sql: str
    error_message: Optional[str]
    retry_count: int
    
    # Execution Phase
    result_data: List[Dict[str, Any]]
    
    # Final Output Phase
    success: bool
    final_answer: str
    
    # Observability
    start_time: float
    latency_ms: float
    trace_steps: List[Dict[str, Any]]
