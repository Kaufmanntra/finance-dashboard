"""
Cashflow analytics — monthly summaries and category breakdowns.
"""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def monthly_summary(engine: Engine) -> pd.DataFrame:
    """
    Return a DataFrame with one row per month across all banks.

    Columns:
        month       (Period)   — e.g. 2024-03
        income      (float)    — sum of positive amounts
        expenses    (float)    — sum of negative amounts (negative value)
        net         (float)    — income + expenses
    """
    sql = text("""
        SELECT
            DATE_TRUNC('month', date)                          AS month,
            COALESCE(SUM(amount) FILTER (WHERE amount > 0), 0) AS income,
            COALESCE(SUM(amount) FILTER (WHERE amount < 0), 0) AS expenses,
            COALESCE(SUM(amount), 0)                           AS net
        FROM transactions
        GROUP BY DATE_TRUNC('month', date)
        ORDER BY month
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    df["month"] = pd.to_datetime(df["month"], utc=True).dt.to_period("M")
    return df


def monthly_by_category(engine: Engine) -> pd.DataFrame:
    """
    Return a pivot table of expenses per month × category.

    Rows = months (newest first), columns = categories, values = absolute spend.
    A 'Total' column is appended on the right.
    """
    sql = text("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', date), 'YYYY-MM') AS month,
            category,
            SUM(amount)                                   AS total
        FROM transactions
        WHERE amount < 0
        GROUP BY 1, 2
        ORDER BY 1 DESC, 2
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    if df.empty:
        return df

    pivot = df.pivot(index="month", columns="category", values="total").fillna(0)
    pivot = pivot.abs()
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.sort_index(ascending=False)
    pivot = pivot.reset_index().rename(columns={"month": "Month"})
    return pivot


def category_breakdown(engine: Engine, months: int = 3) -> pd.DataFrame:
    """
    Return total spent per category for the last N months, expenses only.

    Columns:
        category    (str)
        total       (float)   — sum of amounts (negative)
    """
    safe_months = int(months)
    sql = text(f"""
        SELECT
            category,
            SUM(amount) AS total
        FROM transactions
        WHERE amount < 0
          AND date >= DATE_TRUNC('month', NOW()) - INTERVAL '{safe_months} months'
        GROUP BY category
        ORDER BY total ASC
    """)

    with engine.connect() as conn:
        df = pd.read_sql(sql, conn)

    return df
