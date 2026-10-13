from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "olist.duckdb"

conn = duckdb.connect(str(DB_PATH))

query = """
WITH delivery AS (
    SELECT
        review_score,
        DATE_DIFF(
            'day',
            CAST(order_estimated_delivery_date AS DATE),
            CAST(order_delivered_customer_date AS DATE)
        ) AS delay_days
    FROM mart_orders
    WHERE review_score IS NOT NULL
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
)

SELECT
    review_score,
    COUNT(*) AS orders,
    ROUND(AVG(delay_days), 2) AS avg_difference_from_estimate
FROM delivery
GROUP BY review_score
ORDER BY review_score;
"""

print(conn.execute(query).fetchdf().to_string(index=False))

conn.close()