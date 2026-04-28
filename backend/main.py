"""
QueryMind FastAPI Application

Main entry point for the FastAPI backend. Manages the app lifecycle,
including the asyncpg database connection pool.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from db.connection import create_pool, close_pool, get_pool
from agents.nodes import preload_models
from api.query import router as query_router
from api.analytics import router as analytics_router
from api.embeddings import router as embeddings_router
from config import FRONTEND_URL

logger = logging.getLogger("querymind.main")

# ── Rate Limiting Setup ──────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager.
    - Startup: Initialize asyncpg connection pool and preload models.
    - Shutdown: Close connection pool gracefully.
    """
    logger.info("Starting up QueryMind backend...")
    
    # 1. Initialize DB connection pool
    try:
        await create_pool()
        logger.info("Database connection pool established successfully.")
    except Exception as e:
        logger.error("Failed to establish database connection pool: %s", e)
        raise
    
    # 2. Preload models (Embedding + Groq)
    try:
        await preload_models()
    except Exception as e:
        logger.error("Failed to preload models: %s", e)
        # We don't raise here to allow the app to start, 
        # but models will lazy-load on first request instead.

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

# ── Rate Limiting ────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS Middleware Setup ───────────────────────────────
# In production, we restrict origins to the FRONTEND_URL.
# If credentials=True, origins MUST NOT be ["*"].
origins = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    """Health check endpoint with DB connectivity test."""
    try:
        pool = await get_pool()
        # Simple query to verify DB is reachable
        await pool.fetchval("SELECT 1")
        return {
            "status": "ok", 
            "service": "querymind-backend",
            "database": "connected"
        }
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {
            "status": "error",
            "service": "querymind-backend",
            "database": "disconnected",
            "error": str(e)
        }, 503
