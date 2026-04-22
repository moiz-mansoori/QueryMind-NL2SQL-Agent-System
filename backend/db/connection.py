"""
QueryMind Database Connection Module

Manages the asyncpg connection pool lifecycle for PostgreSQL.
Registers the pgvector codec so vector columns are handled natively.
"""

import logging
from typing import Optional

import asyncpg
from pgvector.asyncpg import register_vector

from config import DB_URL
from config import DB_MIN_POOL_SIZE, DB_MAX_POOL_SIZE

logger = logging.getLogger("querymind.db")

# Global pool reference
_pool: Optional[asyncpg.Pool] = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    """
    Callback executed for every new connection in the pool.
    Registers the pgvector type codec so we can read/write
    vector columns as Python lists/numpy arrays.
    """
    await register_vector(conn)


async def create_pool() -> asyncpg.Pool:
    """
    Create and return the global asyncpg connection pool.
    Registers pgvector codec on each new connection.

    Returns:
        asyncpg.Pool: The initialized connection pool.

    Raises:
        asyncpg.PostgresError: If connection to PostgreSQL fails.
    """
    global _pool
    if _pool is not None:
        logger.warning("Connection pool already exists, returning existing pool")
        return _pool

    try:
        _pool = await asyncpg.create_pool(
            dsn=DB_URL,
            min_size=DB_MIN_POOL_SIZE,
            max_size=DB_MAX_POOL_SIZE,
            init=_init_connection,
            command_timeout=60,
        )
        logger.info(
            "Connection pool created: %s (pool: %d-%d)",
            DB_URL.split('@')[-1] if '@' in DB_URL else "Database",
            DB_MIN_POOL_SIZE, DB_MAX_POOL_SIZE,
        )
        return _pool
    except Exception as e:
        logger.error("Failed to create connection pool: %s", e)
        raise


async def get_pool() -> asyncpg.Pool:
    """
    Get the global connection pool. Creates it if not initialized.

    Returns:
        asyncpg.Pool: The active connection pool.
    """
    global _pool
    if _pool is None:
        _pool = await create_pool()
    return _pool


async def close_pool() -> None:
    """
    Gracefully close the global connection pool.
    Safe to call multiple times.
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Connection pool closed")
    else:
        logger.warning("No connection pool to close")
