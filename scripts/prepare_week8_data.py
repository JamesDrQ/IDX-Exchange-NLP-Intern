"""Prepare a frozen Week 8 sample and blank human-reference review sheets."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/week6_listing_signals.jsonl"
OUTPUT = ROOT / "data/annotations/week8"


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def prepare(source=SOURCE, output=OUTPUT, size=100, dev_size=70, seed=42):
    source, output = Path(source), Path(output)
    if not 0 < dev_size < size:
        raise ValueError("Require 0 < dev_size < size")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite review artifacts: {output}")
    counts = Counter()
    file_hash = hashlib.sha256()
    records = []
    # Connected duplicate groups prevent A/B shared IDs and B/C shared remarks
    # from indirectly leaking across splits. Retain one row per entire group.
    parent = {}

    def find(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    with source.open("rb") as handle:
        for line_number, raw in enumerate(handle, 1):
            file_hash.update(raw)
            row = json.loads(raw)
            counts["source_rows"] += 1
            listing_id = str(row.get("listing_id") or "").strip()
            remarks = row.get("remarks") or ""
            if row.get("error"):
                counts["excluded_extraction_errors"] += 1
                continue
            if not listing_id or not remarks.strip():
                counts["excluded_missing_id_or_remarks"] += 1
                continue
            normalized = " ".join(remarks.casefold().split())
            remark_hash = digest(normalized)
            id_key, text_key = "id:" + listing_id, "text:" + remark_hash
            parent[find(text_key)] = find(id_key)
            records.append((id_key, {
                "listing_id": listing_id,
                "source_line": line_number,
                "remarks": remarks,
                "remarks_sha256": remark_hash,
                "source_fields": row.get("source_fields") or {},
                "candidate_signals": row.get("signals") or {},
                "candidate_signals_status": "machine_extracted_unverified",
            }))
    representatives = {}
    for key, row in records:
        group = find(key)
        if group not in representatives:
            representatives[group] = row
    counts["eligible_rows_before_deduplication"] = len(records)
    counts["duplicate_rows_removed"] = len(records) - len(representatives)
    counts["eligible_unique_groups"] = len(representatives)
    if len(representatives) < size:
        raise ValueError(f"Need {size} unique records; found {len(representatives)}")
    ranked = sorted(representatives.values(), key=lambda row: (
        digest(f"{seed}:{row['listing_id']}:{row['remarks_sha256']}"),
        row["listing_id"],
    ))[:size]
    fields = [
        "listing_id", "remarks", "source_fields_json", "candidate_entities_json",
        "verified_bedrooms", "bedrooms_evidence", "verified_bathrooms",
        "bathrooms_evidence", "verified_price", "price_evidence",
        "verified_location", "location_evidence", "top_feature_1",
        "feature_1_evidence", "top_feature_2", "feature_2_evidence",
        "missing_or_ambiguous_fields", "reference_summary", "reference_status",
        "reviewer", "reviewed_at", "notes",
    ]
    output.mkdir(parents=True)
    split_stats = {}
    for split, rows in (("dev", ranked[:dev_size]), ("test", ranked[dev_size:])):
        missing = Counter()
        with (output / f"{split}_listings.jsonl").open("w", encoding="utf-8") as data, \
                (output / f"{split}_reference_review.csv").open("w", encoding="utf-8", newline="") as review:
            writer = csv.DictWriter(review, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                row["split"] = split
                data.write(json.dumps(row, ensure_ascii=False) + "\n")
                entities = row["candidate_signals"].get("entities") or {}
                for field in ("bedrooms", "bathrooms", "price", "city"):
                    if entities.get(field) is None or entities.get(field) == "":
                        missing[field] += 1
                writer.writerow({
                    "listing_id": row["listing_id"], "remarks": row["remarks"],
                    "source_fields_json": json.dumps(row["source_fields"], ensure_ascii=False),
                    "candidate_entities_json": json.dumps(entities, ensure_ascii=False),
                    "reference_status": "pending_human_authoring",
                })
        split_stats[split] = {
            "records": len(rows), "human_verified_references": 0,
            "missing_candidate_entities": dict(missing),
            "listing_ids": [row["listing_id"] for row in rows],
        }
    artifacts = {}
    for path in sorted(output.iterdir()):
        artifacts[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "source_path": str(source), "source_sha256": file_hash.hexdigest(),
        "seed": seed, "sample_size": size,
        "sampling": "Sort duplicate-group representatives by SHA256(seed:id:remarks_hash); take first N; first dev_size are development.",
        "deduplication": "Connected components by listing ID or casefolded whitespace-normalized remarks; first source row represents each group.",
        "limitations": [
            "Near-duplicate descriptions and relisted properties with different IDs and text are not resolved.",
            "Sample excludes empty remarks and extraction errors; evaluate these separately as edge cases.",
            "Source export lacks structured bedroom/bathroom columns; extracted counts require human verification.",
            "Signals are unverified suggestions, not ground truth. No human reference summaries have been authored.",
        ],
        "counts": dict(counts), "splits": split_stats,
        "initial_artifact_sha256": artifacts,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--dev-size", type=int, default=70)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = prepare(args.source, args.output, args.size, args.dev_size, args.seed)
    print(json.dumps({"output": str(args.output), "counts": result["counts"],
                      "split_sizes": {k: v["records"] for k, v in result["splits"].items()}}, indent=2))


if __name__ == "__main__":
    main()
