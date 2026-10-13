# Olist Weekly Business Review

Analytics and ELT pipeline for the Olist Brazilian E-Commerce marketplace dataset.

## Project Overview

This project builds a small ELT pipeline using Python and DuckDB to transform the Olist e-commerce dataset into analysis-ready data and answer key business questions around revenue, customer retention, delivery performance, and customer satisfaction.

## Tech Stack

- Python
- DuckDB
- Pandas
- Matplotlib
- SQL

## Project Structure

```text
olist-assignment/
├── data/
│   └── raw/
│       └── Olist CSV files
│
├── src/
│   ├── ingest.py
│   ├── transform.py
│   ├── quality_checks.py
│   ├── analysis.py
│   ├── metrics.py
│   └── create_charts.py
│
├── sql/
│   ├── 01_monthly_revenue.sql
│   ├── 02_top_categories.sql
│   ├── 03_rolling_orders.sql
│   ├── 04_repeat_purchase.sql
│   └── 05_delivery_reviews.sql
│
├── reports/
│   ├── monthly_revenue.png
│   ├── rolling_orders.png
│   ├── late_delivery_by_review.png
│   └── customer_experience_metrics.png
│
├── olist.duckdb
├── requirements.txt
└── README.md
Dataset

The project uses the Olist Brazilian E-Commerce Public Dataset.

Download the dataset from Kaggle and place the CSV files inside:

data/raw/

Required files:

olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_customers_dataset.csv
olist_sellers_dataset.csv
olist_products_dataset.csv
olist_geolocation_dataset.csv
product_category_name_translation.csv
Setup

Create a virtual environment:
python3 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt
Pipeline Execution
1. Load raw data
python src/ingest.py

This loads all required CSV files into DuckDB raw tables.

The ingestion process is idempotent using CREATE OR REPLACE TABLE, so repeated runs do not duplicate data.

2. Create staging and mart tables
python src/transform.py

This creates cleaned staging tables and the analysis-ready mart_orders table.

mart_orders contains one row per order with:

Customer information
Order status
Purchase and delivery dates
Item total
Freight total
Payment total
Item count
Review score
Payment mismatch flag
3. Run data-quality checks
python src/quality_checks.py

The pipeline checks:

Null order IDs
Duplicate order IDs
Delivery before purchase
Orders without a customer
Payment total mismatch

The pipeline raises a data-quality alarm and stops if any check fails.

Payment mismatches are flagged rather than silently removed so that the original data remains available for investigation.

4. Run business metrics
python src/metrics.py
5. Generate charts
python src/create_charts.py

Charts are saved in the reports/ directory.

SQL Analysis

The sql/ directory contains five independent SQL analyses.

01 — Monthly Revenue

Calculates monthly revenue and month-over-month revenue growth using LAG().

02 — Top Product Categories

Ranks the top three product categories within each customer state using DENSE_RANK().

03 — 7-Day Rolling Orders

Calculates the daily order count and a true seven-calendar-day rolling average using window functions.

04 — Repeat Purchase Rate

Calculates repeat purchase rate using customer_unique_id rather than the order-level customer ID.

05 — Delivery and Reviews

Measures delivery variance against the estimated delivery date and compares late-delivery rates across review scores.

Key Business Metrics
Metric	Result
Delivered orders	96,470
On-time delivery rate	93.23%
Satisfied review rate (4–5 stars)	78.40%
Average review score	4.16 / 5
Repeat purchase rate	3.04%
Key Finding

Late delivery is strongly associated with lower customer review scores.

The late-delivery rate is:

36.68% for 1-star reviews
18.84% for 2-star reviews
8.78% for 3-star reviews
3.43% for 4-star reviews
1.86% for 5-star reviews

This suggests that reducing late deliveries should be a priority for improving customer satisfaction.

The analysis establishes an association rather than proving causation.

Data Quality Finding

Five data-quality checks were implemented.

Four checks passed with zero failures.

The payment reconciliation check identified 387 orders where:

payment_total != item_total + freight_total

These records were retained and explicitly flagged rather than silently dropped or modified.

Reproducibility

The pipeline is designed to be rerun safely because raw and transformed tables are recreated using idempotent operations.

## End-to-End Pipeline

The complete ELT workflow can also be executed with:

```bash
cd src
python pipeline.py

