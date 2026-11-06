"""Prepare a human-review CSV from Week 6's sampled JSONL.

Usage from project root:
    python -m scripts.prepare_week6_gold --limit 30 --seed 42

All gold fields are left BLANK intentionally. Predicted values are *not* labels.
"""

import argparse
import csv
import json
import random
from pathlib import Path

ENTITIES = ("bedrooms", "bathrooms", "sqft", "price", "city")
FLAGS = ("pool", "private_pool", "community_pool", "garage", "fireplace", "view")
KEYWORDS = ("condition", "financial", "location", "property_type", "view")


def fieldnames():
    names = ["listing_id", "remarks", "source_fields_json"]
    for section, keys in (("entity", ENTITIES), ("flag", FLAGS), ("keyword", KEYWORDS)):
        for key in keys:
            names.extend((f"pred_{section}_{key}", f"gold_{section}_{key}"))
    names.extend(("pred_amenities", "gold_amenities", "review_status", "reviewer_notes"))
    return names


def prediction_cell(value, as_list=False):
    if as_list:
        return json.dumps(value or [], ensure_ascii=False)
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def build_row(sample):
    signals = sample.get("signals")
    if not isinstance(signals, dict):
        raise ValueError(f"Listing {sample.get('listing_id')}: missing valid signals")
    row = {
        "listing_id": str(sample["listing_id"]),
        "remarks": sample.get("remarks") or "",
        "source_fields_json": json.dumps(sample.get("source_fields", {}), ensure_ascii=False, default=str),
        "pred_amenities": prediction_cell(signals.get("amenities"), as_list=True),
        "review_status": "pending",
        "reviewer_notes": "",
    }
    for prefix, container, keys in (
        ("entity", "entities", ENTITIES),
        ("flag", "flags", FLAGS),
        ("keyword", "keywords", KEYWORDS),
    ):
        values = signals.get(container) or {}
        for key in keys:
            row[f"pred_{prefix}_{key}"] = prediction_cell(values.get(key), as_list=prefix == "keyword")
    # Gold fields are never inferred or pre-populated from model output.
    return row


def prepare(input_path, output_path, limit, seed):
    with input_path.open(encoding="utf-8") as source:
        samples = [json.loads(line) for line in source if line.strip()]
    good = [s for s in samples if "error" not in s]
    if len(good) < limit:
        raise ValueError(f"Requested {limit} samples; only {len(good)} error-free rows available")
    rng = random.Random(seed)
    selected = rng.sample(good, limit)
    ids = [str(s["listing_id"]) for s in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("Sample has duplicate listing IDs; resolve before annotation")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames())
        writer.writeheader()
        writer.writerows(build_row(s) for s in selected)
    return len(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/week6_review_sample.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/week6_gold_review.csv"))
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be positive")
    n = prepare(args.input, args.output, args.limit, args.seed)
    print(f"Wrote {n} review rows to {args.output}")
    print("All gold_* fields are BLANK. Review full Remarks + source fields before filling.")
    print("Set review_status=done only after human review. Do not commit raw listing data.")


if __name__ == "__main__":
    main()
