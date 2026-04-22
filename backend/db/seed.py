"""
QueryMind Database Seed Script

Imports Olist CSV data into PostgreSQL and generates schema embeddings.
Run this script after the PostgreSQL container is up:
    python -m db.seed [--reset] [--embeddings-only]
"""

import asyncio
import csv
import logging
import sys
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional

import asyncpg
import numpy as np

# Resolve imports when run as script or module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    DB_URL,
    DATASET_DIR, EMBED_MODEL, EMBED_DIMENSION,
)
from db.models import DDL_ALL, DDL_DROP_ALL

logger = logging.getLogger("querymind.seed")

# ── Column type definitions for proper type coercion ─────
# Maps (table, column) → Python converter function
# Types: 'str', 'int', 'float', 'numeric', 'timestamp'
COLUMN_TYPES = {
    "olist_customers": {
        "customer_id": "str", "customer_unique_id": "str",
        "customer_zip_code_prefix": "str", "customer_city": "str",
        "customer_state": "str",
    },
    "olist_products": {
        "product_id": "str", "product_category_name": "str",
        "product_name_lenght": "int", "product_description_lenght": "int",
        "product_photos_qty": "int", "product_weight_g": "int",
        "product_length_cm": "int", "product_height_cm": "int",
        "product_width_cm": "int",
    },
    "olist_sellers": {
        "seller_id": "str", "seller_zip_code_prefix": "str",
        "seller_city": "str", "seller_state": "str",
    },
    "olist_orders": {
        "order_id": "str", "customer_id": "str", "order_status": "str",
        "order_purchase_timestamp": "timestamp", "order_approved_at": "timestamp",
        "order_delivered_carrier_date": "timestamp",
        "order_delivered_customer_date": "timestamp",
        "order_estimated_delivery_date": "timestamp",
    },
    "olist_order_items": {
        "order_id": "str", "order_item_id": "int",
        "product_id": "str", "seller_id": "str",
        "shipping_limit_date": "timestamp",
        "price": "numeric", "freight_value": "numeric",
    },
    "olist_order_payments": {
        "order_id": "str", "payment_sequential": "int",
        "payment_type": "str", "payment_installments": "int",
        "payment_value": "numeric",
    },
    "olist_order_reviews": {
        "review_id": "str", "order_id": "str", "review_score": "int",
        "review_comment_title": "str", "review_comment_message": "str",
        "review_creation_date": "timestamp", "review_answer_timestamp": "timestamp",
    },
    "olist_geolocation": {
        "geolocation_zip_code_prefix": "str",
        "geolocation_lat": "float", "geolocation_lng": "float",
        "geolocation_city": "str", "geolocation_state": "str",
    },
    "product_category_translation": {
        "product_category_name": "str",
        "product_category_name_english": "str",
    },
}


def _coerce(value: str, col_type: str):
    """Convert a raw CSV string to the appropriate Python type."""
    if value is None or value.strip() == "":
        return None
    value = value.strip()
    if col_type == "str":
        return value
    elif col_type == "int":
        try:
            return int(float(value))  # handles "3.0" → 3
        except (ValueError, TypeError):
            return None
    elif col_type in ("float", "numeric"):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    elif col_type == "timestamp":
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return value

# CSV file → table mapping
CSV_TABLE_MAP = {
    "olist_customers_dataset.csv": {
        "table": "olist_customers",
        "columns": [
            "customer_id", "customer_unique_id",
            "customer_zip_code_prefix", "customer_city", "customer_state",
        ],
    },
    "olist_products_dataset.csv": {
        "table": "olist_products",
        "columns": [
            "product_id", "product_category_name",
            "product_name_lenght", "product_description_lenght",
            "product_photos_qty", "product_weight_g",
            "product_length_cm", "product_height_cm", "product_width_cm",
        ],
    },
    "olist_sellers_dataset.csv": {
        "table": "olist_sellers",
        "columns": [
            "seller_id", "seller_zip_code_prefix",
            "seller_city", "seller_state",
        ],
    },
    "olist_orders_dataset.csv": {
        "table": "olist_orders",
        "columns": [
            "order_id", "customer_id", "order_status",
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    },
    "olist_order_items_dataset.csv": {
        "table": "olist_order_items",
        "columns": [
            "order_id", "order_item_id", "product_id", "seller_id",
            "shipping_limit_date", "price", "freight_value",
        ],
    },
    "olist_order_payments_dataset.csv": {
        "table": "olist_order_payments",
        "columns": [
            "order_id", "payment_sequential", "payment_type",
            "payment_installments", "payment_value",
        ],
    },
    "olist_order_reviews_dataset.csv": {
        "table": "olist_order_reviews",
        "columns": [
            "review_id", "order_id", "review_score",
            "review_comment_title", "review_comment_message",
            "review_creation_date", "review_answer_timestamp",
        ],
    },
    "olist_geolocation_dataset.csv": {
        "table": "olist_geolocation",
        "columns": [
            "geolocation_zip_code_prefix", "geolocation_lat",
            "geolocation_lng", "geolocation_city", "geolocation_state",
        ],
        "has_serial_id": True,
    },
    "product_category_name_translation.csv": {
        "table": "product_category_translation",
        "columns": [
            "product_category_name", "product_category_name_english",
        ],
    },
}

# Import order (dependency-safe)
IMPORT_ORDER = [
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]

# Schema descriptions for embedding generation
TABLE_DESCRIPTIONS = {
    "olist_customers": "Customer information including unique customer ID, location (city, state, zip code). Used to identify buyers and their geographic distribution.",
    "olist_orders": "Order records with status tracking, timestamps for purchase, approval, carrier delivery, customer delivery, and estimated delivery date. Central table linking customers to their purchases.",
    "olist_order_items": "Individual items within each order, linking to products and sellers. Contains price and freight value for each item. One order can have multiple items.",
    "olist_products": "Product catalog with category, physical dimensions (weight, length, height, width), description length, and photo count. Linked from order items.",
    "olist_sellers": "Seller information including location (city, state, zip code). Sellers fulfill orders through the marketplace.",
    "olist_order_payments": "Payment details for each order including payment method (credit card, boleto, voucher, debit card), number of installments, and payment value.",
    "olist_order_reviews": "Customer reviews for orders with a score (1-5), optional comment title and message, and timestamps for review creation and answer.",
    "olist_geolocation": "Brazilian zip code geolocation data with latitude and longitude coordinates, city and state. Used for geographic analysis of customers and sellers.",
    "product_category_translation": "Translation table mapping Portuguese product category names to English. Useful for understanding product categories in English.",
}

COLUMN_DESCRIPTIONS = {
    "olist_customers": {
        "customer_id": "Unique identifier for the customer in the orders dataset. Foreign key used in olist_orders.",
        "customer_unique_id": "Unique identifier for the actual customer. One customer can have multiple customer_ids across orders.",
        "customer_zip_code_prefix": "First 5 digits of the customer's zip code for geographic analysis.",
        "customer_city": "City where the customer is located.",
        "customer_state": "Two-letter state code where the customer is located (e.g., SP, RJ, MG).",
    },
    "olist_orders": {
        "order_id": "Unique identifier for each order. Primary key, used to join with items, payments, and reviews.",
        "customer_id": "Foreign key linking to olist_customers table.",
        "order_status": "Current status: delivered, shipped, canceled, unavailable, processing, created, approved, invoiced.",
        "order_purchase_timestamp": "Timestamp when the customer made the purchase.",
        "order_approved_at": "Timestamp when the payment was approved.",
        "order_delivered_carrier_date": "Timestamp when the order was handed to the logistics carrier.",
        "order_delivered_customer_date": "Timestamp when the customer received the order.",
        "order_estimated_delivery_date": "Estimated delivery date shown to customer at purchase time.",
    },
    "olist_order_items": {
        "order_id": "Foreign key linking to olist_orders. One order can have multiple items.",
        "order_item_id": "Sequential number of the item within the order (1, 2, 3...).",
        "product_id": "Foreign key linking to olist_products table.",
        "seller_id": "Foreign key linking to olist_sellers table. The seller who fulfills this item.",
        "shipping_limit_date": "Deadline for the seller to ship the item to the carrier.",
        "price": "Price of the item in Brazilian Reais (BRL).",
        "freight_value": "Shipping cost for this item in Brazilian Reais (BRL).",
    },
    "olist_products": {
        "product_id": "Unique identifier for each product.",
        "product_category_name": "Product category in Portuguese. Join with product_category_translation for English.",
        "product_name_lenght": "Number of characters in the product name.",
        "product_description_lenght": "Number of characters in the product description.",
        "product_photos_qty": "Number of product photos in the listing.",
        "product_weight_g": "Product weight in grams.",
        "product_length_cm": "Product length in centimeters.",
        "product_height_cm": "Product height in centimeters.",
        "product_width_cm": "Product width in centimeters.",
    },
    "olist_sellers": {
        "seller_id": "Unique identifier for each seller on the marketplace.",
        "seller_zip_code_prefix": "First 5 digits of the seller's zip code.",
        "seller_city": "City where the seller is located.",
        "seller_state": "Two-letter state code where the seller is located.",
    },
    "olist_order_payments": {
        "order_id": "Foreign key linking to olist_orders. One order can have multiple payments.",
        "payment_sequential": "Sequential number if order has multiple payment methods.",
        "payment_type": "Payment method: credit_card, boleto, voucher, debit_card, not_defined.",
        "payment_installments": "Number of installments chosen by the customer for credit card payments.",
        "payment_value": "Total payment amount in Brazilian Reais (BRL).",
    },
    "olist_order_reviews": {
        "review_id": "Unique identifier for each review.",
        "order_id": "Foreign key linking to olist_orders.",
        "review_score": "Customer satisfaction score from 1 (worst) to 5 (best).",
        "review_comment_title": "Optional title of the review comment (in Portuguese).",
        "review_comment_message": "Optional body text of the review comment (in Portuguese).",
        "review_creation_date": "Timestamp when the review survey was sent to the customer.",
        "review_answer_timestamp": "Timestamp when the customer submitted the review.",
    },
    "olist_geolocation": {
        "geolocation_zip_code_prefix": "First 5 digits of the zip code.",
        "geolocation_lat": "Latitude coordinate of the zip code area.",
        "geolocation_lng": "Longitude coordinate of the zip code area.",
        "geolocation_city": "City name for this zip code.",
        "geolocation_state": "Two-letter state code for this zip code.",
    },
    "product_category_translation": {
        "product_category_name": "Product category name in Portuguese (original).",
        "product_category_name_english": "Product category name translated to English.",
    },
}


async def create_connection() -> asyncpg.Connection:
    """
    Create a single asyncpg connection for seeding operations.

    Returns:
        asyncpg.Connection: A direct database connection.
    """
    conn = await asyncpg.connect(DB_URL)
    return conn


async def reset_database(conn: asyncpg.Connection) -> None:
    """
    Drop all tables and recreate the schema from scratch.

    Args:
        conn: Active asyncpg connection.
    """
    logger.warning("Resetting database — dropping all tables...")
    await conn.execute(DDL_DROP_ALL)
    logger.info("All tables dropped successfully")


async def create_schema(conn: asyncpg.Connection) -> None:
    """
    Execute all DDL statements to create the database schema.
    Tables are created in dependency order (referenced tables first).

    Args:
        conn: Active asyncpg connection.
    """
    logger.info("Creating database schema...")
    for table_name, ddl in DDL_ALL:
        try:
            await conn.execute(ddl)
            logger.info("  ✓ Created: %s", table_name)
        except Exception as e:
            logger.error("  ✗ Failed to create %s: %s", table_name, e)
            raise


async def import_csv(
    conn: asyncpg.Connection,
    csv_filename: str,
    config: dict,
) -> int:
    """
    Import a single CSV file into its corresponding PostgreSQL table.

    Uses Python's csv.reader to correctly handle multiline text fields
    (e.g. review comments) and then streams rows via
    ``conn.copy_records_to_table`` for fast bulk insertion.

    Args:
        conn: Active asyncpg connection.
        csv_filename: Name of the CSV file in the Dataset directory.
        config: Table config dict with 'table', 'columns', optional 'has_serial_id'.

    Returns:
        int: Number of rows imported.
    """
    csv_path = DATASET_DIR / csv_filename
    if not csv_path.exists():
        logger.error("CSV file not found: %s", csv_path)
        return 0

    table_name = config["table"]
    columns = config["columns"]

    logger.info("  Importing %s → %s ...", csv_filename, table_name)
    start = time.time()

    try:
        # Get the type map for this table
        type_map = COLUMN_TYPES.get(table_name, {})

        # Read all rows via Python csv module (handles multiline fields)
        records = []
        with open(csv_path, "r", encoding="utf-8-sig") as f:  # utf-8-sig strips BOM
            reader = csv.reader(f)
            header = next(reader)  # skip header

            # Build column index mapping (CSV col order → our col order)
            col_indices = []
            for col in columns:
                try:
                    col_indices.append(header.index(col))
                except ValueError:
                    logger.error("  Column '%s' not found in CSV header: %s", col, header)
                    return 0

            for row in reader:
                if len(row) < len(header):
                    continue  # skip malformed rows
                record = []
                for i, idx in enumerate(col_indices):
                    raw_val = row[idx]
                    col_name = columns[i]
                    col_type = type_map.get(col_name, "str")
                    record.append(_coerce(raw_val, col_type))
                records.append(tuple(record))

        # Bulk insert via copy_records_to_table
        result = await conn.copy_records_to_table(
            table_name,
            records=records,
            columns=columns,
        )
        row_count = int(result.split()[-1])
        elapsed = time.time() - start
        logger.info("  ✓ %s: %d rows imported in %.1fs", table_name, row_count, elapsed)
        return row_count

    except Exception as e:
        logger.error("  Import failed for %s: %s", table_name, e)
        return 0





async def import_all_csvs(conn: asyncpg.Connection) -> dict:
    """
    Import all Olist CSV files into PostgreSQL in dependency order.

    Args:
        conn: Active asyncpg connection.

    Returns:
        dict: Mapping of table names to row counts.
    """
    logger.info("Starting CSV import from: %s", DATASET_DIR)
    results = {}

    for csv_filename in IMPORT_ORDER:
        config = CSV_TABLE_MAP[csv_filename]
        count = await import_csv(conn, csv_filename, config)
        results[config["table"]] = count

    logger.info("CSV import complete. Total tables: %d", len(results))
    return results


async def generate_embeddings(conn: asyncpg.Connection) -> int:
    """
    Generate schema embeddings using sentence-transformers and store
    them in the schema_embeddings table via pgvector.

    Creates embeddings for:
    - Each table (table-level description)
    - Each column (column-level description with table context)

    Args:
        conn: Active asyncpg connection.

    Returns:
        int: Number of embeddings generated.
    """
    logger.info("Loading embedding model: %s ...", EMBED_MODEL)
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL)
    logger.info("Embedding model loaded (dimension: %d)", EMBED_DIMENSION)

    # Clear existing embeddings
    await conn.execute("DELETE FROM schema_embeddings")

    descriptions = []
    metadata = []

    # Table-level descriptions
    for table_name, description in TABLE_DESCRIPTIONS.items():
        text = f"Table: {table_name} — {description}"
        descriptions.append(text)
        metadata.append({
            "table_name": table_name,
            "column_name": None,
            "description": text,
        })

    # Column-level descriptions
    for table_name, columns in COLUMN_DESCRIPTIONS.items():
        for column_name, description in columns.items():
            text = f"Table: {table_name}, Column: {column_name} — {description}"
            descriptions.append(text)
            metadata.append({
                "table_name": table_name,
                "column_name": column_name,
                "description": text,
            })

    # ── Generate all embeddings in one batch 
    logger.info("Generating embeddings for %d descriptions...", len(descriptions))
    embeddings = model.encode(descriptions, show_progress_bar=True)

    # ── Insert into schema_embeddings 
    logger.info("Storing embeddings in pgvector...")
    from pgvector.asyncpg import register_vector
    await register_vector(conn)

    insert_query = """
        INSERT INTO schema_embeddings (table_name, column_name, description, embedding)
        VALUES ($1, $2, $3, $4)
    """

    for i, meta in enumerate(metadata):
        embedding_vector = np.array(embeddings[i], dtype=np.float32)
        await conn.execute(
            insert_query,
            meta["table_name"],
            meta["column_name"],
            meta["description"],
            embedding_vector,
        )

    logger.info("✓ %d embeddings stored in schema_embeddings", len(metadata))
    return len(metadata)


async def verify_tables(conn: asyncpg.Connection) -> None:
    """
    Verify all tables exist and print row counts.

    Args:
        conn: Active asyncpg connection.
    """
    logger.info("Verifying table row counts...")
    tables = [
        "olist_customers", "olist_orders", "olist_order_items",
        "olist_products", "olist_sellers", "olist_order_payments",
        "olist_order_reviews", "olist_geolocation",
        "product_category_translation", "query_logs", "schema_embeddings",
    ]

    for table in tables:
        try:
            row = await conn.fetchrow(f"SELECT COUNT(*) as cnt FROM {table}")
            logger.info("  %s: %d rows", table.ljust(35), row["cnt"])
        except Exception as e:
            logger.error("  %s: ERROR — %s", table.ljust(35), e)


async def run_seed(
    reset: bool = False,
    embeddings_only: bool = False,
) -> None:
    """
    Main seed function. Creates schema, imports CSVs, generates embeddings.

    Args:
        reset: If True, drops all tables before recreating.
        embeddings_only: If True, only regenerates embeddings.
    """
    logger.info("=" * 60)
    logger.info("QueryMind Database Seed")
    logger.info("=" * 60)

    conn = await create_connection()

    try:
        if embeddings_only:
            logger.info("Mode: embeddings-only")
            count = await generate_embeddings(conn)
            logger.info("Generated %d embeddings", count)
        else:
            if reset:
                await reset_database(conn)

            await create_schema(conn)
            await import_all_csvs(conn)
            count = await generate_embeddings(conn)
            logger.info("Generated %d embeddings", count)

        await verify_tables(conn)
    finally:
        await conn.close()
        logger.info("Database connection closed")

    logger.info("=" * 60)
    logger.info("Seed complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="QueryMind Database Seed Script")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables before recreating (DESTRUCTIVE)",
    )
    parser.add_argument(
        "--embeddings-only",
        action="store_true",
        help="Only regenerate schema embeddings",
    )
    args = parser.parse_args()

    asyncio.run(run_seed(reset=args.reset, embeddings_only=args.embeddings_only))
