WITH date_range AS (
    SELECT
        MIN(CAST(order_purchase_timestamp AS DATE)) AS start_date,
        MAX(CAST(order_purchase_timestamp AS DATE)) AS end_date
    FROM raw_orders
),

calendar AS (
    SELECT
        UNNEST(
            generate_series(
                start_date,
                end_date,
                INTERVAL 1 DAY
            )
        )::DATE AS order_date
    FROM date_range
),

daily_orders AS (
    SELECT
        CAST(order_purchase_timestamp AS DATE) AS order_date,
        COUNT(DISTINCT order_id) AS order_count
    FROM raw_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
),

daily_series AS (
    SELECT
        c.order_date,
        COALESCE(d.order_count, 0) AS order_count
    FROM calendar c
    LEFT JOIN daily_orders d
        ON c.order_date = d.order_date
),

rolling_orders AS (
    SELECT
        order_date,
        order_count,
        AVG(order_count) OVER (
            ORDER BY order_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7_day_avg
    FROM daily_series
)

SELECT
    order_date,
    order_count,
    ROUND(rolling_7_day_avg, 2) AS rolling_7_day_avg
FROM rolling_orders
ORDER BY order_date;