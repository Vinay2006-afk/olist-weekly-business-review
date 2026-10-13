from pathlib import Path
import logging
import duckdb
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
DB_PATH = BASE_DIR / "olist.duckdb"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


EXPECTED_COLUMNS = {
    "orders": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_estimated_delivery_date",
    ],
    "order_items": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "price",
        "freight_value",
    ],
    "order_payments": [
        "order_id",
        "payment_value",
    ],
    "order_reviews": [
        "review_id",
        "order_id",
        "review_score",
    ],
    "customers": [
        "customer_id",
        "customer_unique_id",
        "customer_city",
        "customer_state",
    ],
    "sellers": [
        "seller_id",
        "seller_city",
        "seller_state",
    ],
    "products": [
        "product_id",
        "product_category_name",
    ],
    "geolocation": [
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
    ],
    "category_translation": [
        "product_category_name",
        "product_category_name_english",
    ],
}


def check_files():
    missing = []

    for table_name, filename in FILES.items():
        path = DATA_DIR / filename

        if not path.exists():
            missing.append(filename)

    if missing:
        raise FileNotFoundError(
            "Missing required files:\n"
            + "\n".join(f" - {file}" for file in missing)
        )


def validate_columns():
    logging.info("Validating required CSV columns...")

    for table_name, filename in FILES.items():
        path = DATA_DIR / filename

        actual_columns = set(
            pd.read_csv(path, nrows=0).columns
        )

        required_columns = set(
            EXPECTED_COLUMNS[table_name]
        )

        missing_columns = required_columns - actual_columns

        if missing_columns:
            raise ValueError(
                f"Missing required columns in {filename}: "
                + ", ".join(sorted(missing_columns))
            )

        logging.info(
            "Column validation passed: %s",
            filename
        )


def load_raw_tables():
    check_files()
    validate_columns()

    conn = duckdb.connect(str(DB_PATH))

    try:
        for table_name, filename in FILES.items():
            csv_path = DATA_DIR / filename

            logging.info(
                "Loading %s...",
                filename
            )

            conn.execute(f"""
                CREATE OR REPLACE TABLE raw_{table_name} AS
                SELECT *
                FROM read_csv_auto('{csv_path}')
            """)

            count = conn.execute(
                f"SELECT COUNT(*) FROM raw_{table_name}"
            ).fetchone()[0]

            logging.info(
                "Loaded raw_%s: %s rows",
                table_name,
                f"{count:,}"
            )

        logging.info(
            "All raw tables loaded successfully."
        )

    except Exception:
        logging.exception(
            "Pipeline failed while loading raw tables."
        )
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    logging.info(
        "Starting Olist ingestion pipeline..."
    )

    load_raw_tables()

    logging.info(
        "Ingestion pipeline completed."
    )