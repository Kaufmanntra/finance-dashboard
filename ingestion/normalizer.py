"""
Normalizer — merges any number of parsed bank DataFrames into one unified table.

Each parser already returns the same 6 columns:
    date | value_date | type | description | amount | bank

This module adds:
    - deduplication (same transaction imported twice)
    - a stable `id` column (sha256 of date + bank + amount + description)
    - a `category` column populated by a simple keyword classifier
"""

import hashlib
import pandas as pd


# ── Category keyword rules ────────────────────────────────────────────────────
# Order matters: first match wins.
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Investments",    ["wertpapiere", "etf", "isin", "xetra", "wpknr", "kupon", "ertraegnis"]),
    ("Transfers",      ["übertrag", "uebertrag", "überweisung"]),
    ("Fees",           ["entgelt", "verwahrentgelt", "gebühr"]),
    ("Salary",         ["gehalt", "lohn", "salary"]),
    ("Rent",           ["miete", "warmmiete", "nebenkosten"]),
    ("Baumarkt",       ["hellweg","obi"]),
    ("Groceries",      ["rewe", "edeka", "aldi", "lidl", "penny", "netto", "kaufland", "billa"]),
    ("Transport",      ["bvg", "db ", "deutsche bahn", "flixbus", "uber", "taxi", "mvv"]),
    ("Insurance",      ["versicherung", "allianz", "huk", "axa"]),
    ("Subscriptions",  ["netflix", "spotify", "amazon prime", "apple", "gez", "rundfunk"]),
    ("Health",         ["apotheke", "arzt", "kranken", "pharmacy"]),
    ("Dining",         ["restaurant", "café", "cafe", "mcdonalds", "lieferando", "pizza"]),
    ("Shopping",       ["amazon", "zalando", "h&m", "ikea", "saturn", "mediamarkt"]),
]


def categorize(description: str, tx_type: str) -> str:
    """Return a category string for a single transaction."""
    haystack = (str(description) + " " + str(tx_type)).lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in haystack for kw in keywords):
            return category
    return "Other"


def _make_id(row: pd.Series) -> str:
    key = f"{row['date']}|{row['bank']}|{row['amount']}|{row['description']}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def normalize(*dataframes: pd.DataFrame) -> pd.DataFrame:
    """
    Concatenate multiple parsed DataFrames, deduplicate, and enrich.

    Usage:
        from ingestion.parsers import comdirect, dkb
        from ingestion.normalizer import normalize

        df = normalize(
            comdirect.parse("exports/comdirect.csv"),
            dkb.parse("exports/dkb.csv"),
        )
    """
    if not dataframes:
        raise ValueError("At least one DataFrame required.")

    combined = pd.concat(dataframes, ignore_index=True)

    # Enforce column order & types
    combined["date"]        = pd.to_datetime(combined["date"])
    combined["value_date"]  = pd.to_datetime(combined["value_date"])
    combined["amount"]      = combined["amount"].astype(float)
    combined["description"] = combined["description"].fillna("").astype(str)
    combined["type"]        = combined["type"].fillna("").astype(str)

    # Add enrichment columns
    combined["id"]       = combined.apply(_make_id, axis=1)
    combined["category"] = combined.apply(
        lambda r: categorize(r["description"], r["type"]), axis=1
    )

    # Deduplicate on stable id (keeps first occurrence)
    combined = combined.drop_duplicates(subset=["id"])

    # Sort newest first
    combined = combined.sort_values("date", ascending=False).reset_index(drop=True)

    return combined[["id", "date", "value_date", "bank", "type",
                      "description", "amount", "category"]]
