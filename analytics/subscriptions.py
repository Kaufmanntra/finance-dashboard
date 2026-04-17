"""
Subscription / recurring payment detection.
"""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def detect_recurring(engine: Engine) -> pd.DataFrame:
    """
    Find transactions whose description and rounded amount repeat in
    multiple distinct calendar months — a signal for recurring charges.

    A transaction is considered recurring when:
      - It is an expense (amount < 0)
      - The same (description, rounded amount) pair appears in >= 2
        distinct months

    Columns:
        description     (str)
        amount          (float)   — median charge amount (negative)
        frequency       (int)     — number of distinct months observed
        annual_cost     (float)   — |amount| * 12
    """
    sql = text("""
        WITH grouped AS (
            SELECT
                description,
                ROUND(amount::NUMERIC, 0) AS rounded_amount,
                COUNT(DISTINCT DATE_TRUNC('month', date)) AS frequency,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS median_amount
            FROM transactions
            WHERE amount < 0
              AND description <> ''
            GROUP BY description, ROUND(amount::NUMERIC, 0)
            HAVING COUNT(DISTINCT DATE_TRUNC('month', date)) >= 2
        )
        SELECT
            description,
            median_amount::NUMERIC                     AS amount,
            frequency,
            ROUND(ABS(median_amount::NUMERIC) * 12, 2) AS annual_cost
        FROM grouped
        ORDER BY annual_cost DESC
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    return df
