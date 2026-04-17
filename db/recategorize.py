"""
Re-applies CATEGORY_RULES from normalizer to all rows in the transactions table.
Run this whenever rules change to keep stored categories in sync.

Usage:
    python -m db.recategorize
"""

from db.connection import get_connection
from ingestion.normalizer import categorize


def recategorize():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, description, type FROM transactions")
            rows = cur.fetchall()

            updated = 0
            for tx_id, description, tx_type in rows:
                new_category = categorize(description or "", tx_type or "")
                cur.execute(
                    "UPDATE transactions SET category = %s WHERE id = %s AND category != %s",
                    (new_category, tx_id, new_category),
                )
                updated += cur.rowcount

        conn.commit()
        print(f"Done. {updated} of {len(rows)} rows updated.")
    finally:
        conn.close()


if __name__ == "__main__":
    recategorize()
