from pathlib import Path
import logging
import duckdb


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "olist.duckdb"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def run_quality_checks():
    conn = duckdb.connect(str(DB_PATH))

    checks = {}

    try:
        checks["Null order_id"] = conn.execute("""
            SELECT COUNT(*)
            FROM raw_orders
            WHERE order_id IS NULL
        """).fetchone()[0]

        checks["Duplicate order_id"] = conn.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT order_id
                FROM raw_orders
                GROUP BY order_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        checks["Delivery before purchase"] = conn.execute("""
            SELECT COUNT(*)
            FROM stg_orders
            WHERE order_delivered_customer_date IS NOT NULL
              AND order_purchase_timestamp IS NOT NULL
              AND order_delivered_customer_date < order_purchase_timestamp
        """).fetchone()[0]

        checks["Orders without customer"] = conn.execute("""
            SELECT COUNT(*)
            FROM stg_orders o
            LEFT JOIN stg_customers c
                ON o.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
        """).fetchone()[0]

        checks["Payment mismatch"] = conn.execute("""
            SELECT COUNT(*)
            FROM mart_orders
            WHERE payment_mismatch_flag = 1
        """).fetchone()[0]

        checks["Orphan order items"] = conn.execute("""
            SELECT COUNT(*)
            FROM stg_order_items oi
            LEFT JOIN stg_orders o
                ON oi.order_id = o.order_id
            WHERE o.order_id IS NULL
        """).fetchone()[0]

        print("\n========== DATA QUALITY REPORT ==========\n")

        failed = False

        for check_name, failing_rows in checks.items():
            if failing_rows == 0:
                print(
                    f"PASS | {check_name}: "
                    f"{failing_rows:,} failing rows"
                )
            else:
                print(
                    f"FAIL | {check_name}: "
                    f"{failing_rows:,} failing rows"
                )
                failed = True

        print("\n=========================================\n")

        if failed:
            raise RuntimeError(
                "DATA QUALITY ALARM: One or more checks failed."
            )

        print("All data-quality checks passed.")

    finally:
        conn.close()


if __name__ == "__main__":
    run_quality_checks()