import re
import logging
from typing import Dict, Any

import asyncio
from groq import AsyncGroq
from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL, GROQ_API_KEY

logger = logging.getLogger("querymind.agents.nodes.utils")

# Global Model Cache
_embed_model = None
_groq_client = None

def get_embed_model() -> SentenceTransformer:
    """Lazy load the sentence-transformers model to save memory."""
    global _embed_model
    if _embed_model is None:
        logger.info("Loading embedding model %s ...", EMBED_MODEL)
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def get_groq_client() -> AsyncGroq:
    """Get or create a singleton AsyncGroq client."""
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            logger.error("GROQ_API_KEY is missing!")
        _groq_client = AsyncGroq(api_key=GROQ_API_KEY)
    return _groq_client


async def preload_models():
    """Preload models in a separate thread to avoid blocking startup."""
    logger.info("Preloading models (Embedding + Groq)...")
    get_groq_client()
    logger.info("Models preloaded successfully.")


def _format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    """
    Convert the retrieved_schema dict into a human-readable string
    suitable for inclusion in an LLM prompt.
    """
    if not schema:
        return "No schema information available."

    lines = []
    for table_name, columns in schema.items():
        lines.append(f"Table: {table_name}")
        for col in columns:
            col_name = col.get("column", "")
            desc = col.get("description", "")
            if col_name:
                lines.append(f"  - {col_name}: {desc}")
            else:
                lines.append(f"  (table description): {desc}")
        lines.append("")
    return "\n".join(lines)


def _clean_sql_response(raw: str) -> str:
    """
    Strip markdown fences, backticks, and any non-SQL prose from the
    LLM's raw output so we get a clean SQL string.
    """
    text = raw.strip()

    fenced = re.search(r"```(?:sql)?\s*\n?(.*?)\n?```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    text = text.strip("`").strip()

    sql_match = re.search(
        r"((?:SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|EXPLAIN)\b.+)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if sql_match:
        text = sql_match.group(1).strip()

    text = text.rstrip(";")

    return text
