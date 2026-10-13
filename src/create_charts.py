from pathlib import Path
import duckdb
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "olist.duckdb"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(exist_ok=True)

conn = duckdb.connect(str(DB_PATH))


# ---------------------------------------------------------
# Chart 1: Monthly Revenue
# ---------------------------------------------------------

monthly_revenue = conn.execute("""
    SELECT
        DATE_TRUNC(
            'month',
            CAST(order_purchase_timestamp AS TIMESTAMP)
        ) AS month,
        SUM(item_total) AS revenue
    FROM mart_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND CAST(order_purchase_timestamp AS DATE)
          < DATE '2018-09-01'
    GROUP BY 1
    ORDER BY 1
""").fetchdf()

plt.figure(figsize=(10, 5))
plt.plot(
    monthly_revenue["month"],
    monthly_revenue["revenue"]
)
plt.title("Monthly Revenue")
plt.xlabel("Month")
plt.ylabel("Revenue")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(REPORT_DIR / "monthly_revenue.png", dpi=200)
plt.close()


# ---------------------------------------------------------
# Chart 2: 7-Day Rolling Average of Daily Orders
# ---------------------------------------------------------

rolling_orders = conn.execute("""
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
    )

    SELECT
        order_date,
        order_count,
        AVG(order_count) OVER (
            ORDER BY order_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7_day_avg
    FROM daily_series
    ORDER BY order_date
""").fetchdf()

plt.figure(figsize=(10, 5))
plt.plot(
    rolling_orders["order_date"],
    rolling_orders["rolling_7_day_avg"]
)
plt.title("7-Day Rolling Average of Daily Orders")
plt.xlabel("Date")
plt.ylabel("Average Daily Orders")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(REPORT_DIR / "rolling_orders.png", dpi=200)
plt.close()


# ---------------------------------------------------------
# Chart 3: Late Delivery Rate by Review Score
# ---------------------------------------------------------

delivery_reviews = conn.execute("""
    WITH delivery_data AS (
        SELECT
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
    )

    SELECT
        review_score,
        100.0 * AVG(
            CASE
                WHEN delivery_variance_days > 0
                THEN 1
                ELSE 0
            END
        ) AS late_delivery_rate
    FROM delivery_data
    GROUP BY review_score
    ORDER BY review_score
""").fetchdf()

plt.figure(figsize=(8, 5))
plt.bar(
    delivery_reviews["review_score"].astype(str),
    delivery_reviews["late_delivery_rate"]
)
plt.title("Late Delivery Rate by Review Score")
plt.xlabel("Review Score")
plt.ylabel("Late Delivery Rate (%)")
plt.tight_layout()
plt.savefig(REPORT_DIR / "late_delivery_by_review.png", dpi=200)
plt.close()


# ---------------------------------------------------------
# Chart 4: Customer Satisfaction Metrics
# ---------------------------------------------------------

metrics = conn.execute("""
    SELECT
        ROUND(
            100.0 * AVG(
                CASE
                    WHEN review_score >= 4
                    THEN 1
                    ELSE 0
                END
            ),
            2
        ) AS satisfied_rate,

        ROUND(
            100.0 * AVG(
                CASE
                    WHEN
                        order_delivered_customer_date IS NOT NULL
                        AND order_estimated_delivery_date IS NOT NULL
                        AND DATE_DIFF(
                            'day',
                            CAST(order_estimated_delivery_date AS DATE),
                            CAST(order_delivered_customer_date AS DATE)
                        ) <= 0
                    THEN 1
                    ELSE 0
                END
            ),
            2
        ) AS on_time_rate

    FROM mart_orders
    WHERE order_status = 'delivered'
""").fetchdf()

metric_names = ["Satisfied\nOrders", "On-Time\nDelivery"]
metric_values = [
    metrics["satisfied_rate"].iloc[0],
    metrics["on_time_rate"].iloc[0]
]

plt.figure(figsize=(7, 5))
plt.bar(metric_names, metric_values)
plt.title("Customer Experience Guardrail Metrics")
plt.ylabel("Rate (%)")
plt.ylim(0, 100)
plt.tight_layout()
plt.savefig(REPORT_DIR / "customer_experience_metrics.png", dpi=200)
plt.close()


conn.close()

print("Charts created successfully:")
print(" - reports/monthly_revenue.png")
print(" - reports/rolling_orders.png")
print(" - reports/late_delivery_by_review.png")
print(" - reports/customer_experience_metrics.png")