-- Part B: Data Quality Checks

-- 1. Null order_id
SELECT COUNT(*) AS failing_rows
FROM raw_orders
WHERE order_id IS NULL;


-- 2. Duplicate order_id
SELECT COUNT(*) AS failing_rows
FROM (
    SELECT order_id
    FROM raw_orders
    GROUP BY order_id
    HAVING COUNT(*) > 1
);


-- 3. Delivery date before purchase date
SELECT COUNT(*) AS failing_rows
FROM stg_orders
WHERE order_delivered_customer_date IS NOT NULL
  AND order_purchase_timestamp IS NOT NULL
  AND order_delivered_customer_date < order_purchase_timestamp;


-- 4. Orders without a matching customer
SELECT COUNT(*) AS failing_rows
FROM stg_orders o
LEFT JOIN stg_customers c
    ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- 5. Payment total mismatch
SELECT COUNT(*) AS failing_rows
FROM mart_orders
WHERE payment_mismatch_flag = 1;

-- 6. Orphan order items (custom referential-integrity check)
SELECT COUNT(*) AS failing_rows
FROM stg_order_items oi
LEFT JOIN stg_orders o
    ON oi.order_id = o.order_id
WHERE o.order_id IS NULL;