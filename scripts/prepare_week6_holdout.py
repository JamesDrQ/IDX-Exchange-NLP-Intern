"""Create a reproducible 100-listing final Week 6 holdout review CSV from MySQL."""

import argparse
import csv
import json
import os
from pathlib import Path

from scripts.prepare_week6_gold import build_row, fieldnames
from scripts.signal_extractor import SignalExtractor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FINAL_HOLDOUT_SIZE = 100
FINAL_HOLDOUT_SEED = 20261105
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/week6_final_holdout_review.csv"

SELECT_COLUMNS = """
    L_ListingID, L_Remarks, L_SystemPrice, L_City,
    PoolPrivateYN, PoolFeatures, FireplaceYN, FireplaceFeatures,
    GarageYN, ViewYN, View, PropertyCondition
"""


def exclusion_paths(data_root=DEFAULT_DATA_ROOT):
    """Return all existing tabular sample/annotation files under the data tree."""
    if not data_root.exists():
        raise FileNotFoundError(f"Data directory not found: {data_root}")
    return sorted(
        path for path in data_root.rglob("*")
        if path.is_file() and path.suffix.casefold() in {".csv", ".jsonl"}
    )


def load_excluded_ids(paths=None, *, data_root=DEFAULT_DATA_ROOT):
    """Load every prior listing ID from processed samples and review CSVs.

    By default all CSV/JSONL sources under ``data`` are scanned, including
    original development samples, review files, and backups. Passing ``paths``
    keeps the function convenient for isolated tests and callers.
    """
    excluded = set()
    for path in exclusion_paths(data_root) if paths is None else paths:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Listing ID source not found: {path}")
        if path.suffix.casefold() == ".csv":
            with path.open(newline="", encoding="utf-8-sig") as handle:
                for row in csv.DictReader(handle):
                    listing_id = (row.get("listing_id") or row.get("L_ListingID") or "").strip()
                    if listing_id:
                        excluded.add(listing_id)
        else:
            with path.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    listing_id = row.get("listing_id", row.get("L_ListingID"))
                    if listing_id is not None:
                        excluded.add(str(listing_id))
    return excluded


def build_query(excluded_count):
    if excluded_count < 1:
        raise ValueError("At least one development listing ID must be excluded")
    placeholders = ", ".join(["%s"] * excluded_count)
    return f"""
        SELECT {SELECT_COLUMNS}
        FROM real_estate.rets_property
        WHERE L_ListingID IS NOT NULL
          AND CAST(L_ListingID AS CHAR) NOT IN ({placeholders})
        ORDER BY CRC32(CONCAT(CAST(L_ListingID AS CHAR), %s)), L_ListingID
        LIMIT %s
    """


def fetch_holdout_listings(args, excluded_ids):
    """Use the established Week 6 MySQL connection settings and seeded ordering."""
    import mysql.connector
    from scripts.sample_week6_signals import connection_settings

    conn = mysql.connector.connect(**connection_settings(args))
    try:
        cursor = conn.cursor(dictionary=True)
        try:
            sql = build_query(len(excluded_ids))
            params = [*sorted(excluded_ids), str(args.seed), args.limit]
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        conn.close()


def write_holdout_csv(listings, output_path, extractor, excluded_ids):
    """Extract current predictions and write blank Gold fields in review schema."""
    prepared = []
    seen = set()
    for listing in listings:
        listing_id = str(listing.get("L_ListingID") or "").strip()
        if not listing_id:
            raise ValueError("Database returned a listing without L_ListingID")
        if listing_id in seen:
            raise ValueError(f"Database returned duplicate listing ID {listing_id}")
        if listing_id in excluded_ids:
            raise ValueError(f"Development listing {listing_id} appeared in holdout results")
        seen.add(listing_id)
        signals = extractor.extract_signals(listing)
        prepared.append(build_row({
            "listing_id": listing_id,
            "remarks": listing.get("L_Remarks") or "",
            "source_fields": {
                key: value for key, value in listing.items()
                if key not in {"L_ListingID", "L_Remarks"}
            },
            "signals": signals,
        }))

    if len(prepared) != FINAL_HOLDOUT_SIZE:
        raise ValueError(
            f"Expected exactly {FINAL_HOLDOUT_SIZE} final holdout listings; received {len(prepared)}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing holdout file: {output_path}")
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames())
        writer.writeheader()
        writer.writerows(prepared)
    return len(prepared)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=FINAL_HOLDOUT_SIZE)
    parser.add_argument("--seed", type=int, default=FINAL_HOLDOUT_SEED)
    parser.add_argument("--host", default=os.getenv("IDX_MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("IDX_MYSQL_PORT", "3306")))
    parser.add_argument(
        "--output", type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()
    if args.limit != FINAL_HOLDOUT_SIZE:
        parser.error(f"--limit is fixed at {FINAL_HOLDOUT_SIZE} for the final independent holdout")
    if args.output.exists():
        parser.error(f"refusing to overwrite existing output: {args.output}")

    excluded = load_excluded_ids()
    listings = fetch_holdout_listings(args, excluded)
    count = write_holdout_csv(listings, args.output, SignalExtractor(), excluded)
    print(f"Wrote {count} holdout listings to {args.output} (seed={args.seed})")
    print(f"Excluded {len(excluded)} unique IDs from prior data samples and review files")
    print("Gold fields are blank and review_status is pending for manual annotation.")


if __name__ == "__main__":
    main()
