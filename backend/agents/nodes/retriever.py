import logging
from typing import Dict, Any

from db.connection import get_pool
from agents.state import QueryState
from agents.nodes.utils import get_embed_model

logger = logging.getLogger("querymind.agents.nodes.retriever")

async def schema_retriever(state: QueryState) -> Dict[str, Any]:
    """
    Node 1: Retrieves relevant database schema definitions using vector search.
    """
    question = state.get("user_question", "")
    trace_steps = list(state.get("trace_steps", []))
    
    logger.info("Retrieving schema for question: %s", question)
    
    try:
        model = get_embed_model()
        query_embedding = model.encode(question).tolist()
        
        pool = await get_pool()
        
        query = """
            SELECT table_name, column_name, description 
            FROM schema_embeddings
            ORDER BY embedding <=> $1::vector
            LIMIT 5
        """
        
        rows = await pool.fetch(query, query_embedding)
        
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
