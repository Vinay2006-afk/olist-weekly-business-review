WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC(
            'month',
            CAST(order_purchase_timestamp AS TIMESTAMP)
        ) AS month,
        SUM(item_total) AS revenue
    FROM mart_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
),

revenue_with_previous AS (
    SELECT
        month,
        revenue,
        LAG(revenue) OVER (
            ORDER BY month
        ) AS previous_month_revenue
    FROM monthly_revenue
)

SELECT
    month,
    ROUND(revenue, 2) AS revenue,
    ROUND(previous_month_revenue, 2) AS previous_month_revenue,
    ROUND(
        100.0 * (revenue - previous_month_revenue)
        / NULLIF(previous_month_revenue, 0),
        2
    ) AS growth_percentage
FROM revenue_with_previous
ORDER BY month;