"""Extract Week 6 signals for listings in real_estate.rets_property.

Run from the project root with ``python -m scripts.process_week6_listings``.
Database credentials use the existing IDX_MYSQL_*/MYSQL_*/DB_* environment
variables (or the interactive username/password prompts from sample_week6_signals).
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

import mysql.connector

from scripts.sample_week6_signals import connection_settings
from scripts.signal_extractor import SignalExtractor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/week6_listing_signals.jsonl"
SELECT_SQL = """
SELECT
    L_ListingID, L_Remarks, L_SystemPrice, L_City,
    PoolPrivateYN, PoolFeatures, FireplaceYN, FireplaceFeatures,
    GarageYN, ViewYN, View, PropertyCondition
FROM real_estate.rets_property
WHERE L_ListingID IS NOT NULL
"""


def _record(listing, extractor):
    listing_id = listing.get("L_ListingID")
    remarks = listing.get("L_Remarks") or ""
    source_fields = {
        key: value for key, value in listing.items()
        if key not in {"L_ListingID", "L_Remarks"}
    }
    try:
        signals = extractor.extract_signals(listing)
        return {
            "listing_id": str(listing_id),
            "remarks": remarks,
            "source_fields": source_fields,
            "signals": signals,
        }, None
    except Exception as exc:  # keep a row-level failure visible without stopping the batch
        return {
            "listing_id": str(listing_id),
            "remarks": remarks,
            "source_fields": source_fields,
            "error": f"{type(exc).__name__}: {exc}",
        }, exc


def process_listings(args, *, extractor=None, connect=None):
    """Stream rows to an atomic JSONL output; return processing statistics."""
    if args.batch_size < 1:
        raise ValueError("batch_size must be positive")
    if args.limit is not None and args.limit < 1:
        raise ValueError("limit must be positive")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    extractor = extractor or SignalExtractor()
    connect = connect or mysql.connector.connect
    conn = connect(**connection_settings(args))
    cursor = None
    temp_path = None
    stats = {"processed": 0, "errors": 0, "missing_remarks": 0}
    try:
        cursor = conn.cursor(dictionary=True)
        query = SELECT_SQL
        params = ()
        if args.limit is not None:
            query += "LIMIT %s"
            params = (args.limit,)
        cursor.execute(query, params)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=output.parent,
            prefix=f".{output.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            while True:
                rows = cursor.fetchmany(args.batch_size)
                if not rows:
                    break
                for listing in rows:
                    row, error = _record(listing, extractor)
                    handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
                    stats["processed"] += 1
                    stats["errors"] += error is not None
                    stats["missing_remarks"] += not bool(listing.get("L_Remarks"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
        temp_path = None
        return stats
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            try:
                conn.close()
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="maximum rows (useful for smoke tests)")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    stats = process_listings(args)
    print(f"Wrote {stats['processed']} listing records to {args.output}")
    print(f"Extraction errors: {stats['errors']}; records with missing Remarks: {stats['missing_remarks']}")


if __name__ == "__main__":
    main()
