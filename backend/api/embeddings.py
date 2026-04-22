"""
QueryMind Embeddings API Router

Provides an admin endpoint to regenerate schema embeddings on demand.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.connection import get_pool
from db.seed import generate_embeddings

logger = logging.getLogger("querymind.api.embeddings")

router = APIRouter(tags=["embeddings"])

class RebuildResponse(BaseModel):
    status: str
    embeddings_count: int

@router.post("/rebuild", response_model=RebuildResponse)
async def rebuild_embeddings() -> RebuildResponse:
    """
    Rebuild the schema_embeddings table.
    - Generates descriptions.
    - Truncates existing schema_embeddings and inserts new vectors.
    """
    logger.info("Received request to rebuild schema embeddings.")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            count = await generate_embeddings(conn)
        logger.info(f"Successfully rebuilt {count} schema embeddings.")
        return RebuildResponse(status="success", embeddings_count=count)
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild embeddings: {str(e)}",
        )
