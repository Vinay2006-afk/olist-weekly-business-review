WITH delivery_data AS (
    SELECT
        order_id,
        review_score,

        DATE_DIFF(
            'day',
            CAST(order_estimated_delivery_date AS DATE),
            CAST(order_delivered_customer_date AS DATE)
        ) AS delivery_variance_days

    FROM mart_orders

    WHERE order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND review_score IS NOT NULL
),

review_summary AS (
    SELECT
        review_score,
        COUNT(*) AS order_count,

        ROUND(
            AVG(delivery_variance_days),
            2
        ) AS avg_delivery_variance_days,

        ROUND(
            100.0 * AVG(
                CASE
                    WHEN delivery_variance_days > 0
                    THEN 1
                    ELSE 0
                END
            ),
            2
        ) AS late_delivery_rate_percentage

    FROM delivery_data

    GROUP BY review_score
)

SELECT
    review_score,
    order_count,
    avg_delivery_variance_days,
    late_delivery_rate_percentage

FROM review_summary

ORDER BY review_score;