"""Read-only Week 6 spot-check against real_estate.rets_property.

Copy to scripts/sample_week6_signals.py and run from repository root:
    python -m scripts.sample_week6_signals --limit 100

Requires mysql-connector-python, access to MySQL on the host/port you specify,
and an existing scripts.signal_extractor.SignalExtractor implementation.
"""

import argparse
from collections import Counter
from getpass import getpass
import json
import os
from pathlib import Path

import mysql.connector

from scripts.signal_extractor import SignalExtractor


SQL = """
SELECT
    L_ListingID, L_Remarks, L_SystemPrice, L_City,
    PoolPrivateYN, PoolFeatures, FireplaceYN, FireplaceFeatures,
    GarageYN, ViewYN, View, PropertyCondition
FROM real_estate.rets_property
WHERE L_ListingID IS NOT NULL
ORDER BY CRC32(CONCAT(L_ListingID, %s))
LIMIT %s
"""


def connection_settings(args):
    user = (
        os.getenv("IDX_MYSQL_USER") or os.getenv("MYSQL_USER") or os.getenv("DB_USER")
        or input("MySQL username [root]: ").strip() or "root"
    )
    password = (
        os.getenv("IDX_MYSQL_PASSWORD") or os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD")
    )
    if password is None:
        password = getpass("MySQL password (Enter if blank): ")
    host = args.host or os.getenv("IDX_MYSQL_HOST") or os.getenv("MYSQL_HOST") or os.getenv("DB_HOST") or "127.0.0.1"
    port = args.port or int(os.getenv("IDX_MYSQL_PORT") or os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or "3306")
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": "real_estate",
        "connection_timeout": 10,
    }


def fetch_sample(args):
    conn = mysql.connector.connect(**connection_settings(args))
    try:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(SQL, (str(args.seed), args.limit))
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--output", type=Path, default=Path("data/processed/week6_review_sample.jsonl"))
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000 (this is a spot-check tool)")

    listings = fetch_sample(args)
    extractor = SignalExtractor()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    flags = {k: Counter() for k in ("pool", "private_pool", "garage", "fireplace", "view")}
    errors = 0
    keyword_counts = Counter()
    with args.output.open("w", encoding="utf-8") as output:
        for listing in listings:
            try:
                signals = extractor.extract_signals(listing)
                for key, value in signals.get("flags", {}).items():
                    if key in flags:
                        flags[key][str(value)] += 1
                for category, terms in signals.get("keywords", {}).items():
                    keyword_counts[category] += len(terms)
                row = {
                    "listing_id": listing["L_ListingID"],
                    "remarks": listing.get("L_Remarks"),
                    "source_fields": {k: v for k, v in listing.items() if k not in ("L_ListingID", "L_Remarks")},
                    "signals": signals,
                }
            except Exception as exc:
                errors += 1
                row = {
                    "listing_id": listing.get("L_ListingID"),
                    "remarks": listing.get("L_Remarks"),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            output.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    print(f"Wrote {len(listings)} sampled listings to {args.output} (errors: {errors})")
    for name, counter in flags.items():
        print(f"  {name}: {dict(counter)}")
    print("  keyword matches by category:", dict(keyword_counts))
    print("Review rows for false positives, missed signals, and source-field conflicts.")
    print("Do not commit raw listing sample data unless project policy allows it.")


if __name__ == "__main__":
    main()
