"""
QueryMind Database Models (DDL)

Contains all SQL DDL statements for creating the QueryMind database schema.
Includes the 9 Olist e-commerce tables, query_logs for observability,
and schema_embeddings for pgvector-based schema retrieval.
"""

# Enable pgvector extension 
DDL_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS vector;
"""

# Olist Customers
DDL_CUSTOMERS = """
CREATE TABLE IF NOT EXISTS olist_customers (
    customer_id              VARCHAR(64) PRIMARY KEY,
    customer_unique_id       VARCHAR(64) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city            VARCHAR(100),
    customer_state           VARCHAR(2)
);
CREATE INDEX IF NOT EXISTS idx_customers_unique_id
    ON olist_customers (customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_customers_zip
    ON olist_customers (customer_zip_code_prefix);
"""

# Olist Orders 
DDL_ORDERS = """
CREATE TABLE IF NOT EXISTS olist_orders (
    order_id                       VARCHAR(64) PRIMARY KEY,
    customer_id                    VARCHAR(64) NOT NULL
        REFERENCES olist_customers(customer_id),
    order_status                   VARCHAR(20),
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON olist_orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status
    ON olist_orders (order_status);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts
    ON olist_orders (order_purchase_timestamp);
"""

# Olist Products 
DDL_PRODUCTS = """
CREATE TABLE IF NOT EXISTS olist_products (
    product_id                 VARCHAR(64) PRIMARY KEY,
    product_category_name      VARCHAR(100),
    product_name_lenght        INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty         INTEGER,
    product_weight_g           INTEGER,
    product_length_cm          INTEGER,
    product_height_cm          INTEGER,
    product_width_cm           INTEGER
);
CREATE INDEX IF NOT EXISTS idx_products_category
    ON olist_products (product_category_name);
"""

# Olist Sellers 
DDL_SELLERS = """
CREATE TABLE IF NOT EXISTS olist_sellers (
    seller_id              VARCHAR(64) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(10),
    seller_city            VARCHAR(100),
    seller_state           VARCHAR(2)
);
CREATE INDEX IF NOT EXISTS idx_sellers_state
    ON olist_sellers (seller_state);
"""

# Olist Order Items
DDL_ORDER_ITEMS = """
CREATE TABLE IF NOT EXISTS olist_order_items (
    order_id            VARCHAR(64) NOT NULL
        REFERENCES olist_orders(order_id),
    order_item_id       INTEGER NOT NULL,
    product_id          VARCHAR(64) NOT NULL
        REFERENCES olist_products(product_id),
    seller_id           VARCHAR(64) NOT NULL
        REFERENCES olist_sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10,2),
    freight_value       NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON olist_order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
    ON olist_order_items (seller_id);
"""

# Olist Order Payments
DDL_ORDER_PAYMENTS = """
CREATE TABLE IF NOT EXISTS olist_order_payments (
    order_id             VARCHAR(64) NOT NULL
        REFERENCES olist_orders(order_id),
    payment_sequential   INTEGER NOT NULL,
    payment_type         VARCHAR(30),
    payment_installments INTEGER,
    payment_value        NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);
CREATE INDEX IF NOT EXISTS idx_payments_type
    ON olist_order_payments (payment_type);
"""

# ── Olist Order Reviews ──────────────────────────────────
DDL_ORDER_REVIEWS = """
CREATE TABLE IF NOT EXISTS olist_order_reviews (
    review_id               VARCHAR(64) NOT NULL,
    order_id                VARCHAR(64) NOT NULL
        REFERENCES olist_orders(order_id),
    review_score            INTEGER,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);
CREATE INDEX IF NOT EXISTS idx_reviews_order_id
    ON olist_order_reviews (order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_score
    ON olist_order_reviews (review_score);
"""

# ── Olist Geolocation ────────────────────────────────────
DDL_GEOLOCATION = """
CREATE TABLE IF NOT EXISTS olist_geolocation (
    id                           SERIAL PRIMARY KEY,
    geolocation_zip_code_prefix  VARCHAR(10),
    geolocation_lat              DOUBLE PRECISION,
    geolocation_lng              DOUBLE PRECISION,
    geolocation_city             VARCHAR(100),
    geolocation_state            VARCHAR(2)
);
CREATE INDEX IF NOT EXISTS idx_geolocation_zip
    ON olist_geolocation (geolocation_zip_code_prefix);
CREATE INDEX IF NOT EXISTS idx_geolocation_state
    ON olist_geolocation (geolocation_state);
"""

# ── Product Category Translation ─────────────────────────
DDL_CATEGORY_TRANSLATION = """
CREATE TABLE IF NOT EXISTS product_category_translation (
    product_category_name         VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);
"""

# ── Query Logs (Observability) ───────────────────────────
DDL_QUERY_LOGS = """
CREATE TABLE IF NOT EXISTS query_logs (
    id             SERIAL PRIMARY KEY,
    user_question  TEXT NOT NULL,
    generated_sql  TEXT,
    final_sql      TEXT,
    result_rows    INTEGER DEFAULT 0,
    error_msg      TEXT,
    retries        INTEGER DEFAULT 0,
    latency_ms     DOUBLE PRECISION DEFAULT 0,
    success        BOOLEAN DEFAULT FALSE,
    trace_data     JSONB,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at
    ON query_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_success
    ON query_logs (success);
"""

# ── Schema Embeddings (pgvector) ─────────────────────────
DDL_SCHEMA_EMBEDDINGS = """
CREATE TABLE IF NOT EXISTS schema_embeddings (
    id          SERIAL PRIMARY KEY,
    table_name  VARCHAR(100) NOT NULL,
    column_name VARCHAR(100),
    description TEXT NOT NULL,
    embedding   vector(384) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_schema_embeddings_table
    ON schema_embeddings (table_name);
"""

# ── Ordered list: tables must be created in dependency order ──
DDL_ALL = [
    ("extensions",              DDL_EXTENSIONS),
    ("olist_customers",         DDL_CUSTOMERS),
    ("olist_products",          DDL_PRODUCTS),
    ("olist_sellers",           DDL_SELLERS),
    ("olist_orders",            DDL_ORDERS),
    ("olist_order_items",       DDL_ORDER_ITEMS),
    ("olist_order_payments",    DDL_ORDER_PAYMENTS),
    ("olist_order_reviews",     DDL_ORDER_REVIEWS),
    ("olist_geolocation",       DDL_GEOLOCATION),
    ("product_category_translation", DDL_CATEGORY_TRANSLATION),
    ("query_logs",              DDL_QUERY_LOGS),
    ("schema_embeddings",       DDL_SCHEMA_EMBEDDINGS),
]

# ── Drop order (reverse dependency) for clean reset ──────
DDL_DROP_ALL = """
DROP TABLE IF EXISTS schema_embeddings CASCADE;
DROP TABLE IF EXISTS query_logs CASCADE;
DROP TABLE IF EXISTS olist_order_reviews CASCADE;
DROP TABLE IF EXISTS olist_order_payments CASCADE;
DROP TABLE IF EXISTS olist_order_items CASCADE;
DROP TABLE IF EXISTS olist_geolocation CASCADE;
DROP TABLE IF EXISTS product_category_translation CASCADE;
DROP TABLE IF EXISTS olist_orders CASCADE;
DROP TABLE IF EXISTS olist_sellers CASCADE;
DROP TABLE IF EXISTS olist_products CASCADE;
DROP TABLE IF EXISTS olist_customers CASCADE;
"""
