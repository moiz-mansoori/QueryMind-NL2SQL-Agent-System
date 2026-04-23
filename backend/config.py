"""
QueryMind Configuration Module

Loads all environment variables from .env file and exports
typed configuration constants used across the application.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ──────────────────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# ── Logging Setup ────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("querymind")

# ── Groq API ─────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── PostgreSQL ───────────────────────────────────────────
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_USER: str = os.getenv("DB_USER", "querymind")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "querymind_secret")
DB_NAME: str = os.getenv("DB_NAME", "querymind")
DB_URL: str = os.getenv(
    "DB_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)
DB_MIN_POOL_SIZE: int = int(os.getenv("DB_MIN_POOL_SIZE", "2"))
DB_MAX_POOL_SIZE: int = int(os.getenv("DB_MAX_POOL_SIZE", "10"))

# ── Agent Configuration ──────────────────────────────────
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RESULT_LIMIT: int = int(os.getenv("RESULT_LIMIT", "500"))

# ── Embedding Model ─────────────────────────────────────
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_DIMENSION: int = int(os.getenv("EMBED_DIMENSION", "384"))

# ── Server ───────────────────────────────────────────────
BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_HOST: str = os.getenv("FRONTEND_HOST", "0.0.0.0")
FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "5000"))
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Paths ────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATASET_DIR: Path = Path(os.getenv("DATASET_DIR", str(PROJECT_ROOT / "Dataset")))

# ── Known Schema (for validation) ────────────────────────
KNOWN_TABLES: set = {
    "olist_customers",
    "olist_orders",
    "olist_order_items",
    "olist_products",
    "olist_sellers",
    "olist_order_payments",
    "olist_order_reviews",
    "olist_geolocation",
    "product_category_translation",
}
