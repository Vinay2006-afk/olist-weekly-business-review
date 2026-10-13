from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "olist.duckdb"

conn = duckdb.connect(str(DB_PATH))

query = """
WITH delivered AS (
    SELECT
        order_id,
        review_score,
        order_delivered_customer_date,
        order_estimated_delivery_date,

        DATE_DIFF(
            'day',
            CAST(order_estimated_delivery_date AS DATE),
            CAST(order_delivered_customer_date AS DATE)
        ) AS delivery_variance_days

    FROM mart_orders

    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
),

metrics AS (
    SELECT
        COUNT(*) AS delivered_orders,

        ROUND(
            100.0 * AVG(
                CASE
                    WHEN delivery_variance_days <= 0
                    THEN 1
                    ELSE 0
                END
            ),
            2
        ) AS on_time_delivery_rate,

        ROUND(
            100.0 * AVG(
                CASE
                    WHEN review_score >= 4
                    THEN 1
                    ELSE 0
                END
            ),
            2
        ) AS satisfied_review_rate,

        ROUND(
            AVG(review_score),
            2
        ) AS average_review_score

    FROM delivered
)

SELECT *
FROM metrics;
"""

print(conn.execute(query).fetchdf().to_string(index=False))

conn.close()