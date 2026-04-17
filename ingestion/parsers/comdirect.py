"""
Parser for Comdirect Girokonto / Verrechnungskonto CSV exports.

Format details (reverse-engineered from real export):
- Encoding:   latin-1
- Separator:  semicolon (;)
- Header:     4 rows of metadata (skip them)
- Columns:    Buchungstag | Wertstellung (Valuta) | Vorgang | Buchungstext | Umsatz in EUR | (empty)
- Footer:     last row contains "Alter Kontostand" — must be dropped
- Amounts:    German locale, e.g. "-1.200,87" → needs cleanup before float conversion
- Dates:      DD.MM.YYYY
"""

import pandas as pd
from pathlib import Path


def parse(filepath: str | Path) -> pd.DataFrame:
    """
    Read a Comdirect CSV export and return a normalized DataFrame.

    Returns columns:
        date        (datetime64)  — Buchungstag
        value_date  (datetime64)  — Wertstellung
        type        (str)         — Vorgang (e.g. "Übertrag / Überweisung")
        description (str)         — Buchungstext, stripped of leading whitespace
        amount      (float)       — signed EUR amount
        bank        (str)         — always "comdirect"
    """
    df = pd.read_csv(
        filepath,
        sep=";",
        encoding="latin-1",
        skiprows=4,          # skip 3 metadata rows + blank row
        header=0,
        dtype=str,
    )

    # Drop the trailing "Alter Kontostand" footer row and any fully-empty rows
    df = df[df["Buchungstag"].notna()]
    df = df[~df["Buchungstag"].str.startswith("Alter Kontostand", na=False)]

    # Drop the spurious trailing empty column
    df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])

    out = pd.DataFrame()
    out["date"]        = pd.to_datetime(df["Buchungstag"], format="%d.%m.%Y")
    out["value_date"]  = pd.to_datetime(df["Wertstellung (Valuta)"], format="%d.%m.%Y")
    out["type"]        = df["Vorgang"].str.strip()
    out["description"] = df["Buchungstext"].str.strip()
    out["amount"]      = (
        df["Umsatz in EUR"]
        .str.replace(".", "", regex=False)   # remove thousands separator
        .str.replace(",", ".", regex=False)  # decimal comma → point
        .astype(float)
    )
    out["bank"] = "comdirect"

    return out.reset_index(drop=True)


# ── quick smoke-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_comdirect.csv"
    df = parse(path)
    print(df.to_string())
    print(f"\n{len(df)} rows  |  total: {df['amount'].sum():,.2f} EUR")
