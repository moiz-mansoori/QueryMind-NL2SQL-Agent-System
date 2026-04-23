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
    Rebuild the entire database and schema embeddings.
    - Creates tables (if not exist).
    - Imports CSV data (skips heavy geolocation on production).
    - Generates and stores schema embeddings.
    """
    from db.seed import create_schema, import_all_csvs, generate_embeddings
    
    logger.info("Received request to rebuild database and embeddings.")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # 1. Ensure tables exist
            await create_schema(conn)
            
            # 2. Import CSV data (Skip geolocation to avoid Render OOM)
            await import_all_csvs(conn, skip_geolocation=True)
            
            # 3. Generate embeddings
            count = await generate_embeddings(conn)
            
        logger.info(f"Successfully initialized database with {count} schema embeddings.")
        return RebuildResponse(status="success", embeddings_count=count)
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild embeddings: {str(e)}",
        )
