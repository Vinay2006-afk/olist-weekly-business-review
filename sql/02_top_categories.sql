WITH category_revenue AS (
    SELECT
        c.customer_state,
        COALESCE(t.product_category_name_english,
                 p.product_category_name,
                 'unknown') AS product_category,
        SUM(oi.price) AS revenue
    FROM raw_orders o

    JOIN raw_customers c
        ON o.customer_id = c.customer_id

    JOIN raw_order_items oi
        ON o.order_id = oi.order_id

    JOIN raw_products p
        ON oi.product_id = p.product_id

    LEFT JOIN raw_category_translation t
        ON p.product_category_name = t.product_category_name

    WHERE o.order_status NOT IN ('canceled', 'unavailable')

    GROUP BY
        c.customer_state,
        product_category
),

ranked_categories AS (
    SELECT
        customer_state,
        product_category,
        revenue,
        DENSE_RANK() OVER (
            PARTITION BY customer_state
            ORDER BY revenue DESC
        ) AS category_rank
    FROM category_revenue
)

SELECT
    customer_state,
    product_category,
    ROUND(revenue, 2) AS revenue,
    category_rank
FROM ranked_categories
WHERE category_rank <= 3
ORDER BY
    customer_state,
    category_rank,
    revenue DESC;