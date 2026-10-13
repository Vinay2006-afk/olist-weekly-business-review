import logging

from ingest import load_raw_tables
from transform import transform
from quality_checks import run_quality_checks


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


def run_pipeline():
    logging.info("========== OLIST ELT PIPELINE START ==========")

    logging.info("STEP 1/3 - Loading raw data")
    load_raw_tables()

    logging.info("STEP 2/3 - Creating staging tables and mart")
    transform()

    logging.info("STEP 3/3 - Running data-quality checks")
    run_quality_checks()

    logging.info("========== OLIST ELT PIPELINE COMPLETED ==========")


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception:
        logging.exception("PIPELINE FAILED")
        raise