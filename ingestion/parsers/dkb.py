"""
Parser for DKB (Deutsche Kreditbank) CSV exports.

Format details:
- Encoding:   utf-8-sig (with BOM)
- Separator:  semicolon (;)
- Header:     rows 0-5 are metadata; actual column header is at row 5 (0-indexed)
- Columns:    Buchungsdatum | Wertstellung | Status | Zahlungspflichtige*r |
              Zahlungsempfänger*in | Verwendungszweck | Gläubiger-ID |
              Mandatsreferenz | Kundenreferenz | Betrag (€) | Gläubiger-ID
- Footer:     none (clean)
- Amounts:    German locale, e.g. "-1.234,56"
- Dates:      DD.MM.YY  (two-digit year!)
"""

import pandas as pd
from pathlib import Path


def parse(filepath: str | Path) -> pd.DataFrame:
    """
    Read a DKB CSV export and return a normalized DataFrame.

    Returns columns:
        date        (datetime64)  — Buchungsdatum
        value_date  (datetime64)  — Wertstellung
        type        (str)         — derived from Zahlungspflichtige / Zahlungsempfänger
        description (str)         — Verwendungszweck
        amount      (float)       — signed EUR amount
        bank        (str)         — always "dkb"
    """
    # DKB header row index varies slightly between exports; probe for it.
    # The real header row contains "Buchungsdatum" in the first column.
    header_row = _find_header_row(filepath)

    df = pd.read_csv(
        filepath,
        sep=";",
        encoding="utf-8-sig",
        skiprows=header_row,
        header=0,
        dtype=str,
    )

    # Drop completely empty rows that sometimes appear at the end
    df = df.dropna(how="all")

    # Normalise column names (strip whitespace / special chars for safety)
    df.columns = [c.strip() for c in df.columns]

    out = pd.DataFrame()

    # DKB uses DD.MM.YY (two-digit year) — dayfirst=True, format explicit
    def parse_date(col):
        return pd.to_datetime(df[col], format="%d.%m.%y", errors="coerce")

    out["date"]        = parse_date("Buchungsdatum")
    out["value_date"]  = parse_date("Wertstellung")

    # Build a human-readable type: prefer Zahlungsempfänger, fall back to payer
    out["type"] = (
        df.get("Zahlungsempfänger*in", pd.Series(dtype=str)).str.strip()
        .where(df.get("Zahlungsempfänger*in", pd.Series(dtype=str)).str.strip().ne(""), other=None)
    )
    out["description"] = df.get("Verwendungszweck", pd.Series(dtype=str)).str.strip()
    out["amount"] = (
        df["Betrag (€)"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    out["bank"] = "dkb"

    return out.reset_index(drop=True)


def _find_header_row(filepath: str | Path) -> int:
    """Return the 0-based index of the row containing 'Buchungsdatum'."""
    with open(filepath, encoding="utf-8-sig", errors="replace") as f:
        for i, line in enumerate(f):
            if "Buchungsdatum" in line:
                return i
    raise ValueError(f"Could not locate DKB header row in {filepath}")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_dkb.csv"
    df = parse(path)
    print(df.to_string())
    print(f"\n{len(df)} rows  |  total: {df['amount'].sum():,.2f} EUR")
