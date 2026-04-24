"""
QueryMind Embeddings API Router

Provides admin endpoints to initialize the database and regenerate schema embeddings.
Split into two steps to avoid OOM on Render Free Tier (512MB RAM limit).
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.connection import get_pool

logger = logging.getLogger("querymind.api.embeddings")

router = APIRouter(tags=["embeddings"])


class SeedResponse(BaseModel):
    status: str
    message: str
    tables_created: int = 0
    rows_imported: int = 0


class RebuildResponse(BaseModel):
    status: str
    embeddings_count: int


@router.post("/seed", response_model=SeedResponse)
async def seed_database() -> SeedResponse:
    """
    Step 1: Create tables and import CSV data.
    Does NOT load the AI model, so it stays under 512MB.
    """
    from db.seed import create_schema, import_all_csvs

    logger.info("Step 1/2: Creating schema and importing CSV data...")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await create_schema(conn)
            results = await import_all_csvs(conn, skip_geolocation=True)

        total_rows = sum(results.values())
        logger.info(f"Step 1/2 complete: {len(results)} tables, {total_rows} rows imported.")
        return SeedResponse(
            status="success",
            message=f"Database seeded: {len(results)} tables, {total_rows} rows imported. Now call POST /embeddings/rebuild to generate AI embeddings.",
            tables_created=len(results),
            rows_imported=total_rows,
        )
    except Exception as e:
        logger.error(f"Database seed failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database seed failed: {str(e)}")


@router.post("/rebuild", response_model=RebuildResponse)
async def rebuild_embeddings() -> RebuildResponse:
    """
    Step 2: Generate schema embeddings using sentence-transformers.
    Call this AFTER /embeddings/seed has completed.
    """
    from db.seed import generate_embeddings

    logger.info("Step 2/2: Generating schema embeddings...")
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            count = await generate_embeddings(conn)
        logger.info(f"Step 2/2 complete: {count} schema embeddings generated.")
        return RebuildResponse(status="success", embeddings_count=count)
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rebuild embeddings: {str(e)}",
        )
