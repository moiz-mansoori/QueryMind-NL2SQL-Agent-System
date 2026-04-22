"""
QueryMind FastAPI Application

Main entry point for the FastAPI backend. Manages the app lifecycle,
including the asyncpg database connection pool.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.connection import create_pool, close_pool
from api.query import router as query_router
from api.analytics import router as analytics_router
from api.embeddings import router as embeddings_router

logger = logging.getLogger("querymind.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager.
    - Startup: Initialize asyncpg connection pool.
    - Shutdown: Close connection pool gracefully.
    """
    logger.info("Starting up QueryMind backend...")
    
    # Initialize DB connection pool
    try:
        await create_pool()
        logger.info("Database connection pool established successfully.")
    except Exception as e:
        logger.error("Failed to establish database connection pool: %s", e)
        # We don't raise here so the app can still start and return 500s 
        # instead of failing out completely, but in production we might want to fail hard.
        raise
        
    yield  # Yield control to FastAPI
    
    logger.info("Shutting down QueryMind backend...")
    # Close DB connection pool
    await close_pool()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="QueryMind API",
    description="Backend API for the QueryMind NL2SQL Agent System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API Routers ────────────────────────────────────
app.include_router(query_router, prefix="", tags=["query"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(embeddings_router, prefix="/embeddings", tags=["embeddings"])


# Base Routes
@app.get("/health", tags=["system"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "querymind-backend"}
