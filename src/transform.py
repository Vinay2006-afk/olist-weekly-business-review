from pathlib import Path
import logging
import duckdb


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "olist.duckdb"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def create_staging_tables(conn):
    logging.info("Creating cleaned staging tables...")

    conn.execute("""
        CREATE OR REPLACE TABLE stg_orders AS
        SELECT
            TRIM(order_id) AS order_id,
            TRIM(customer_id) AS customer_id,
            TRIM(order_status) AS order_status,
            TRY_CAST(order_purchase_timestamp AS TIMESTAMP)
                AS order_purchase_timestamp,
            TRY_CAST(order_approved_at AS TIMESTAMP)
                AS order_approved_at,
            TRY_CAST(order_delivered_carrier_date AS TIMESTAMP)
                AS order_delivered_carrier_date,
            TRY_CAST(order_delivered_customer_date AS TIMESTAMP)
                AS order_delivered_customer_date,
            TRY_CAST(order_estimated_delivery_date AS TIMESTAMP)
                AS order_estimated_delivery_date
        FROM raw_orders
    """)

    conn.execute("""
        CREATE OR REPLACE TABLE stg_customers AS
        SELECT
            TRIM(customer_id) AS customer_id,
            TRIM(customer_unique_id) AS customer_unique_id,
            customer_zip_code_prefix,
            TRIM(customer_city) AS customer_city,
            TRIM(customer_state) AS customer_state
        FROM raw_customers
    """)

    conn.execute("""
        CREATE OR REPLACE TABLE stg_order_items AS
        SELECT
            TRIM(order_id) AS order_id,
            order_item_id,
            TRIM(product_id) AS product_id,
            TRIM(seller_id) AS seller_id,
            price,
            freight_value
        FROM raw_order_items
    """)

    conn.execute("""
        CREATE OR REPLACE TABLE stg_payments AS
        SELECT
            TRIM(order_id) AS order_id,
            payment_sequential,
            TRIM(payment_type) AS payment_type,
            payment_installments,
            payment_value
        FROM raw_order_payments
    """)

    conn.execute("""
        CREATE OR REPLACE TABLE stg_reviews AS
        SELECT
            TRIM(review_id) AS review_id,
            TRIM(order_id) AS order_id,
            review_score,
            TRY_CAST(review_creation_date AS TIMESTAMP)
                AS review_creation_date,
            TRY_CAST(review_answer_timestamp AS TIMESTAMP)
                AS review_answer_timestamp
        FROM raw_order_reviews
    """)

    logging.info("Cleaned staging tables created successfully.")


def create_mart(conn):
    logging.info("Creating analysis-ready mart...")

    conn.execute("""
        CREATE OR REPLACE TABLE mart_orders AS

        WITH item_totals AS (
            SELECT
                order_id,
                SUM(price) AS item_total,
                SUM(freight_value) AS freight_total,
                COUNT(*) AS item_count
            FROM stg_order_items
            GROUP BY order_id
        ),

        payment_totals AS (
            SELECT
                order_id,
                SUM(payment_value) AS payment_total
            FROM stg_payments
            GROUP BY order_id
        ),

        latest_reviews AS (
            SELECT
                order_id,
                review_score
            FROM (
                SELECT
                    order_id,
                    review_score,
                    ROW_NUMBER() OVER (
                        PARTITION BY order_id
                        ORDER BY
                            review_creation_date DESC,
                            review_answer_timestamp DESC
                    ) AS rn
                FROM stg_reviews
            )
            WHERE rn = 1
        )

        SELECT
            o.order_id,
            o.customer_id,
            c.customer_unique_id,
            c.customer_city,
            c.customer_state,

            o.order_status,

            o.order_purchase_timestamp,
            o.order_approved_at,
            o.order_delivered_carrier_date,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date,

            i.item_total,
            i.freight_total,
            i.item_count,

            p.payment_total,

            CASE
                WHEN p.payment_total IS NULL
                    OR i.item_total IS NULL
                    OR i.freight_total IS NULL
                    THEN NULL
                WHEN ABS(
                    p.payment_total - (i.item_total + i.freight_total)
                ) > 0.01
                    THEN 1
                ELSE 0
            END AS payment_mismatch_flag,

            r.review_score

        FROM stg_orders o

        LEFT JOIN stg_customers c
            ON o.customer_id = c.customer_id

        LEFT JOIN item_totals i
            ON o.order_id = i.order_id

        LEFT JOIN payment_totals p
            ON o.order_id = p.order_id

        LEFT JOIN latest_reviews r
            ON o.order_id = r.order_id
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM mart_orders"
    ).fetchone()[0]

    logging.info(
        "mart_orders created successfully: %s rows",
        f"{count:,}"
    )

    # Validate one row per order
    duplicate_orders = conn.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT order_id
            FROM mart_orders
            GROUP BY order_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    if duplicate_orders > 0:
        raise RuntimeError(
            f"Mart validation failed: {duplicate_orders} duplicate order_id groups found."
        )

    logging.info("One-row-per-order validation passed.")


def transform():
    conn = duckdb.connect(str(DB_PATH))

    try:
        create_staging_tables(conn)
        create_mart(conn)

    except Exception:
        logging.exception("Transformation pipeline failed.")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    transform()