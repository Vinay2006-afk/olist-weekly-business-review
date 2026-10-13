from pathlib import Path
import duckdb
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "olist.duckdb"
REPORT_DIR = BASE_DIR / "reports"
OUTPUT_PDF = REPORT_DIR / "olist_weekly_business_review.pdf"

REPORT_DIR.mkdir(exist_ok=True)

PAGE_W, PAGE_H = 8.27, 11.69


def new_page(title):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.patch.set_facecolor("white")
    fig.text(0.07, 0.955, title, fontsize=20, fontweight="bold")
    return fig


conn = duckdb.connect(str(DB_PATH))

# -------------------------
# Metrics
# -------------------------
metrics = conn.execute("""
    SELECT
        COUNT(*) AS delivered_orders,
        ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2),
        ROUND(AVG(review_score), 2),
        ROUND(100.0 * AVG(
            CASE
                WHEN DATE_DIFF(
                    'day',
                    CAST(order_estimated_delivery_date AS DATE),
                    CAST(order_delivered_customer_date AS DATE)
                ) <= 0 THEN 1 ELSE 0
            END
        ), 2)
    FROM mart_orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND review_score IS NOT NULL
""").fetchone()

delivered_orders, satisfied_rate, average_review, on_time_rate = metrics

repeat_rate = conn.execute("""
    WITH customer_orders AS (
        SELECT
            c.customer_unique_id,
            COUNT(DISTINCT o.order_id) AS order_count
        FROM raw_orders o
        JOIN raw_customers c ON o.customer_id = c.customer_id
        WHERE o.order_status NOT IN ('canceled', 'unavailable')
        GROUP BY c.customer_unique_id
    )
    SELECT ROUND(
        100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)
        / COUNT(*), 2
    )
    FROM customer_orders
""").fetchone()[0]

payment_mismatches = conn.execute("""
    SELECT COUNT(*)
    FROM mart_orders
    WHERE payment_mismatch_flag = 1
""").fetchone()[0]

monthly_revenue = conn.execute("""
    SELECT
        DATE_TRUNC('month', CAST(order_purchase_timestamp AS TIMESTAMP)) AS month,
        SUM(item_total) AS revenue
    FROM mart_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND CAST(order_purchase_timestamp AS DATE) < DATE '2018-09-01'
    GROUP BY 1
    ORDER BY 1
""").fetchdf()

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
        COUNT(*) AS order_count,
        ROUND(AVG(delivery_variance_days), 2) AS avg_delivery_variance,
        ROUND(100.0 * AVG(
            CASE WHEN delivery_variance_days > 0 THEN 1 ELSE 0 END
        ), 2) AS late_rate
    FROM delivery_data
    GROUP BY review_score
    ORDER BY review_score
""").fetchdf()

rolling = conn.execute("""
    WITH date_range AS (
        SELECT
            MIN(CAST(order_purchase_timestamp AS DATE)) AS start_date,
            MAX(CAST(order_purchase_timestamp AS DATE)) AS end_date
        FROM raw_orders
    ),
    calendar AS (
        SELECT UNNEST(generate_series(
            start_date, end_date, INTERVAL 1 DAY
        ))::DATE AS order_date
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
        LEFT JOIN daily_orders d ON c.order_date = d.order_date
    )
    SELECT
        order_date,
        AVG(order_count) OVER (
            ORDER BY order_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_7_day_avg
    FROM daily_series
    ORDER BY order_date
""").fetchdf()


with PdfPages(OUTPUT_PDF) as pdf:

    # PAGE 1
    fig = new_page("Weekly Business Review — Olist Marketplace")
    fig.text(0.07, 0.915, "VP Executive Memo", fontsize=13, fontweight="bold")

    kpis = [
        ("Satisfied orders", f"{satisfied_rate:.2f}%"),
        ("On-time delivery", f"{on_time_rate:.2f}%"),
        ("Avg review score", f"{average_review:.2f} / 5"),
        ("Repeat purchase", f"{repeat_rate:.2f}%"),
    ]

    for x, (label, value) in zip([0.07, 0.30, 0.53, 0.76], kpis):
        fig.text(x, 0.855, value, fontsize=15, fontweight="bold")
        fig.text(x, 0.827, label, fontsize=8)

    memo = f"""
KEY FINDING

Late delivery is strongly associated with lower customer satisfaction.
Only 1.86% of 5-star orders were delivered after the estimated date,
compared with 36.68% of 1-star orders.

Across {delivered_orders:,} delivered orders, the marketplace achieved
{on_time_rate:.2f}% on-time delivery and a {average_review:.2f}/5 average
review score.


EVIDENCE

• 1-star reviews: 36.68% late-delivery rate
• 2-star reviews: 18.84%
• 3-star reviews: 8.78%
• 4-star reviews: 3.43%
• 5-star reviews: 1.86%

The observed late-delivery rate for 1-star orders is roughly 20 times
the rate observed for 5-star orders.


RECOMMENDATION

Prioritize a delivery-exception management program. Flag orders at
high risk of missing their estimated delivery date before the promised
date. Route these orders to an operational exception queue for carrier
escalation or proactive customer communication.

Track late-delivery rate and 4–5-star satisfaction weekly by carrier,
state and delivery lane to identify where intervention has the greatest
impact.

The analysis shows association, not proven causation.
"""

    fig.text(
        0.07, 0.785, memo,
        fontsize=9.8, verticalalignment="top",
        linespacing=1.45
    )
    fig.text(
        0.07, 0.055,
        "North Star: satisfied delivered orders = delivered orders with a 4–5 star review / delivered orders with a review.",
        fontsize=7.5, style="italic"
    )
    pdf.savefig(fig)
    plt.close(fig)

    # PAGE 2
    fig = new_page("Data Quality & Pipeline")

    fig.text(
        0.07, 0.895,
        "DATA QUALITY CHECKS",
        fontsize=12, fontweight="bold"
    )

    quality = f"""
Check                                      Failing rows
---------------------------------------------------------
Null order_id                                  0
Duplicate order_id                             0
Delivery before purchase                       0
Orders without customer                        0
Payment mismatch                             {payment_mismatches}

Four checks passed with zero failing rows.
"""
    fig.text(
        0.07, 0.855, quality,
        fontsize=9.5, verticalalignment="top",
        family="monospace", linespacing=1.45
    )

    fig.text(
        0.07, 0.615,
        "PAYMENT MISMATCH HANDLING",
        fontsize=12, fontweight="bold"
    )

    handling = f"""
The payment reconciliation check identified {payment_mismatches} orders
where payment_total did not equal item_total + freight_total.

These records were FLAGGED rather than dropped or modified. Original
values remain available for investigation, while mart_orders contains
an explicit payment_mismatch_flag. This preserves completeness and
prevents potentially valid payment-related records from being silently
removed.
"""
    fig.text(
        0.07, 0.58, handling,
        fontsize=9.5, verticalalignment="top",
        linespacing=1.45
    )

    fig.text(
        0.07, 0.365,
        "PIPELINE DESIGN",
        fontsize=12, fontweight="bold"
    )

    pipeline = """
1. Raw CSV ingestion
2. Required-file and required-column validation
3. Cleaned staging tables
4. One-row-per-order analysis mart
5. SQL data-quality validation
6. Pipeline stops with an error when a check fails

The pipeline is idempotent: raw, staging and mart tables use
CREATE OR REPLACE TABLE, so reruns do not append duplicate data.

FAILURE HANDLING

The end-to-end pipeline reached the quality stage and intentionally
stopped because the payment mismatch check detected 387 failing rows.
"""
    fig.text(
        0.07, 0.33, pipeline,
        fontsize=9.5, verticalalignment="top",
        linespacing=1.45
    )

    pdf.savefig(fig)
    plt.close(fig)

    # PAGE 3
    fig = new_page("SQL Analysis & Metric Definitions")

    sql_text = f"""
PART C — SQL RESULTS

1. Monthly revenue and MoM growth
   Uses LAG() to compare each month with the previous month.
   August 2018 revenue (last complete month analysed):
   ₹{monthly_revenue.iloc[-1]["revenue"]:,.2f}

2. Top 3 product categories by customer state
   Uses DENSE_RANK() partitioned by customer state.

3. 7-day rolling average of daily orders
   Uses a continuous calendar so zero-order days are included.

4. Repeat-purchase rate
   Uses customer_unique_id across multiple orders.
   Result: {repeat_rate:.2f}%

5. Delivery performance vs review score
   1-star late rate: {delivery_reviews.iloc[0]["late_rate"]:.2f}%
   5-star late rate: {delivery_reviews.iloc[-1]["late_rate"]:.2f}%


PART D — METRIC DEFINITIONS

NORTH STAR — SATISFIED DELIVERED ORDER RATE
Formula: delivered orders with a 4–5 star review /
         delivered orders with a review × 100
Current value: {satisfied_rate:.2f}%
Why: Directly measures satisfactory delivered experiences.

SUPPORTING — ON-TIME DELIVERY RATE
Formula: delivered orders on/before estimated date /
         eligible delivered orders × 100
Current value: {on_time_rate:.2f}%
Why: Measures delivery reliability.

SUPPORTING — AVERAGE REVIEW SCORE
Formula: sum of review scores / reviewed delivered orders
Current value: {average_review:.2f} / 5
Why: Measures overall customer experience quality.

SUPPORTING — REPEAT PURCHASE RATE
Formula: repeat customers / qualifying customers × 100
Current value: {repeat_rate:.2f}%
Why: Measures whether customers return.

GUARDRAIL — MONTHLY REVENUE
Formula: sum of item price across qualifying orders.
Why: Ensures customer-experience improvements are considered alongside
commercial performance.
"""

    fig.text(
        0.07, 0.89, sql_text,
        fontsize=9.1, verticalalignment="top",
        linespacing=1.42
    )

    pdf.savefig(fig)
    plt.close(fig)

    # PAGE 4
    fig = new_page("Business Trends")

    ax1 = fig.add_axes([0.10, 0.55, 0.82, 0.30])
    ax1.plot(monthly_revenue["month"], monthly_revenue["revenue"])
    ax1.set_title("Monthly Revenue — Complete Months")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Revenue")
    ax1.tick_params(axis="x", rotation=45)

    ax2 = fig.add_axes([0.10, 0.10, 0.82, 0.30])
    ax2.plot(rolling["order_date"], rolling["rolling_7_day_avg"])
    ax2.set_title("7-Day Rolling Average of Daily Orders")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Average Daily Orders")
    ax2.tick_params(axis="x", rotation=45)

    pdf.savefig(fig)
    plt.close(fig)

    # PAGE 5
    fig = new_page("Customer Experience")

    ax1 = fig.add_axes([0.12, 0.55, 0.78, 0.29])
    ax1.bar(
        delivery_reviews["review_score"].astype(str),
        delivery_reviews["late_rate"]
    )
    ax1.set_title("Late Delivery Rate by Review Score")
    ax1.set_xlabel("Review Score")
    ax1.set_ylabel("Late Delivery Rate (%)")

    ax2 = fig.add_axes([0.18, 0.12, 0.64, 0.27])
    ax2.bar(
        ["Satisfied\nOrders", "On-Time\nDelivery"],
        [satisfied_rate, on_time_rate]
    )
    ax2.set_title("Customer Experience Metrics")
    ax2.set_ylabel("Rate (%)")
    ax2.set_ylim(0, 100)

    pdf.savefig(fig)
    plt.close(fig)


conn.close()

print("PDF report created successfully:")
print(OUTPUT_PDF)