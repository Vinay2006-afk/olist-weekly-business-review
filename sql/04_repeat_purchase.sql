WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM raw_orders o
    JOIN raw_customers c
        ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),

customer_summary AS (
    SELECT
        COUNT(*) AS total_customers,
        SUM(
            CASE
                WHEN order_count > 1 THEN 1
                ELSE 0
            END
        ) AS repeat_customers
    FROM customer_orders
)

SELECT
    total_customers,
    repeat_customers,
    ROUND(
        100.0 * repeat_customers / NULLIF(total_customers, 0),
        2
    ) AS repeat_purchase_rate_percentage
FROM customer_summary;