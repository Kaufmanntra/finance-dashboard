
# Finance App – Project Context

## Goal
Personal finance visualization as a local web app.
CSV exports from Comdirect and DKB are parsed,
normalized, stored in PostgreSQL, and displayed as a dashboard.

## Stack
- Python 3.11
- pandas – CSV parsing and data processing
- PostgreSQL (local) – main database
- psycopg2 – Python/PostgreSQL connector
- SQLAlchemy – ORM / query builder
- Dash by Plotly – web app and charts
- No external APIs, everything runs locally

## Project Structure
- ingestion/parsers/comdirect.py – parser for Comdirect CSV exports
- ingestion/parsers/dkb.py      – parser for DKB CSV exports
- ingestion/normalizer.py       – unified schema + transaction categorization
- db/schema.sql                 – PostgreSQL table definitions
- db/queries.py                 – all SQL queries in one place
- db/connection.py              – DB connection (loaded from .env)
- analytics/                    – cashflow, subscriptions, KPI calculations
- app.py                        – Dash entry point

## Database
- Engine: PostgreSQL (local)
- Access: psql, pgAdmin, and Python via psycopg2/SQLAlchemy
- Credentials stored in .env (never commit to Git!)

## Table: transactions
- id          TEXT PRIMARY KEY  (sha256 hash for deduplication)
- date        DATE
- value_date  DATE
- bank        TEXT              (comdirect | dkb)
- type        TEXT              (transaction type)
- description TEXT
- amount      NUMERIC(12,2)     (EUR, negative = expense)
- category    TEXT
- created_at  TIMESTAMPTZ       DEFAULT now()

## CSV Formats
- comdirect: encoding latin-1, semicolon-separated, 4 header rows, footer row
- DKB: encoding utf-8-sig, semicolon-separated, header row position varies per export

## Conventions
- All amounts as float in EUR (negative = expense, positive = income)
- Every parser must return the same 6 columns:
  date | value_date | type | description | amount | bank
- Category