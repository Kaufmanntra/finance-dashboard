"""
Load a bank CSV export into the PostgreSQL transactions table.

Usage:
    python -m ingestion.load <filepath> <bank>

Arguments:
    filepath  Path to the CSV export file
    bank      Bank name: comdirect | dkb
"""

import sys
from ingestion.parsers import comdirect, dkb
from ingestion.normalizer import normalize
from db.connection import get_connection

PARSERS = {
    "comdirect": comdirect.parse,
    "dkb": dkb.parse,
}

INSERT_SQL = """
    INSERT INTO transactions (id, date, value_date, bank, type, description, amount, category)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
"""


def load(filepath: str, bank: str) -> None:
    if bank not in PARSERS:
        print(f"Unknown bank '{bank}'. Choose from: {', '.join(PARSERS)}")
        sys.exit(1)

    df = PARSERS[bank](filepath)
    df = normalize(df)

    rows = [
        (
            row.id,
            row.date.date(),
            row.value_date.date(),
            row.bank,
            row.type,
            row.description,
            float(row.amount),
            row.category,
        )
        for row in df.itertuples(index=False)
    ]

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            inserted = 0
            for row in rows:
                cur.execute(INSERT_SQL, row)
                inserted += cur.rowcount
        conn.commit()
    finally:
        conn.close()

    skipped = len(rows) - inserted
    print(f"Processed {len(rows)} transactions: {inserted} inserted, {skipped} skipped (duplicates).")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m ingestion.load <filepath> <bank>")
        sys.exit(1)

    load(filepath=sys.argv[1], bank=sys.argv[2])
