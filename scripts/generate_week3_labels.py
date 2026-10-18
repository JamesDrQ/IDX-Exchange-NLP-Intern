
import json
from pathlib import Path

from scripts.annotation_helper import generate_candidates

INPUT_PATH = Path("data/labeled/week3_annotations.jsonl")
OUTPUT_PATH = Path("data/labeled/week3_auto_labels.jsonl")

# Load existing 250 annotation records
with INPUT_PATH.open("r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

# Avoid overwriting previous generated data
if OUTPUT_PATH.exists():
    raise FileExistsError(f"Output already exists: {OUTPUT_PATH}")

auto_records = []

for record in records:
    text = record["text"]

    # Automatically generate entity spans
    predicted_entities = generate_candidates(text)

    auto_records.append({
        "source_row": record["source_row"],
        "listing_id": record["listing_id"],
        "text": text,
        "entities": predicted_entities,
        "label_source": "regex",
        "human_verified": False,
    })

# Save automated labels separately
with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    for record in auto_records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"Processed listings: {len(auto_records)}")
print(f"Saved to: {OUTPUT_PATH}")

total_entities = sum(
    len(record["entities"]) for record in auto_records
)

print(f"Total predicted entities: {total_entities}")

print("\nSample prediction:")
first = auto_records[0]

for start, end, label in first["entities"]:
    print(f"{label:10} {first['text'][start:end]}")
