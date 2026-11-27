# Finance Dashboard

A self-hosted dashboard for personal finances. It imports CSV exports from
**DKB** and **comdirect**, stores the transactions in PostgreSQL and shows them
in a Dash web app. Everything runs locally: no bank APIs, no cloud services.

## Features

- **KPIs:** average monthly income, expenses and net, plus savings rate
- **Cash flow:** income, expenses and net per month
- **Categories:** expense share per category over the last 3 months, and a month-by-category table
- **Recurring transactions:** detects subscriptions and other payments that repeat across months
- **Deep dive:** all transactions of one category in a given month, with a total
- Rule-based categorization (keywords in [`ingestion/normalizer.py`](ingestion/normalizer.py))
- Deduplication, so the same export can be imported more than once without creating duplicates

## Stack

Python 3.12 · pandas · PostgreSQL · SQLAlchemy / psycopg2 · Dash + Plotly · Docker Compose

## Quick start with Docker

```bash
cp .env.example .env        # set a strong DB_PASSWORD and DASH_PASSWORD
docker compose up -d --build
```

The dashboard runs at http://localhost:8050. The database schema is created
automatically when the database starts for the first time.

### Importing bank exports

Put your CSV exports into `Import Data/` (this folder is git-ignored), then run:

```bash
docker compose run --rm app python -m ingestion.load "/app/import/<file>.csv" dkb        # or: comdirect
docker compose restart app   # the dashboard loads its data at startup
```

## Local development

Requires Python 3.11+ and a running PostgreSQL instance.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # point it at your database
python -m db.init_db        # create the transactions table
python -m ingestion.load "Import Data/<file>.csv" dkb
python app.py               # http://127.0.0.1:8050
```

After changing the category rules, apply them to existing transactions with:

```bash
python -m db.recategorize
```

## Project structure

```
ingestion/
  parsers/comdirect.py   comdirect CSV parser (latin-1, 4 header rows, footer row)
  parsers/dkb.py         DKB CSV parser (utf-8-sig, variable header position)
  normalizer.py          unified schema, categorization, deduplication
  load.py                CLI: parse a CSV and insert it into the database
db/
  schema.sql             table definition
  connection.py          DB connection, configured via .env
  init_db.py             applies schema.sql
  recategorize.py        re-applies category rules to stored transactions
analytics/
  cashflow.py            monthly summaries and category breakdowns
  subscriptions.py       recurring payment detection
app.py                   Dash app
```

## Security

The dashboard is protected by **HTTP Basic Auth**. Set `DASH_USER` and
`DASH_PASSWORD` in `.env`; the app refuses to start without them. The browser
asks for the login once and remembers it until it is closed.

Basic Auth over plain HTTP sends the password unencrypted, so anyone who can
sniff traffic on your network could read it. That is acceptable on a trusted
home network; for more protection put a reverse proxy with TLS (e.g. Caddy)
in front of the app. Do not expose port 8050 to the internet. From outside,
reach it through a VPN (e.g. WireGuard or Tailscale).

Keep `.env` and your bank exports out of version control. Both are already
listed in `.gitignore`.
