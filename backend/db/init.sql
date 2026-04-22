-- QueryMind — PostgreSQL Initialization
-- This script runs automatically when the
-- PostgreSQL container starts for the first time.
-- It enables the pgvector extension.

CREATE EXTENSION IF NOT EXISTS vector;

-- Confirm extension is active
DO $$
BEGIN
    RAISE NOTICE 'pgvector extension enabled successfully';
END
$$;
