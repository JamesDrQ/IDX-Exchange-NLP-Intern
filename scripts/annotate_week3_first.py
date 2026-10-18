
import json
import re

from scripts.entity_extractor import EntityExtractor

path = "data/labeled/week3_annotations.jsonl"

with open(path, encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

record = records[0]
text = record["text"]

extractor = EntityExtractor()
entities = []

patterns = {
    "BEDROOM": r"\b\d+\s*-\s*bedrooms?\b",
    "BATHROOM": r"\b\d+(?:\.\d+)?\s*-\s*bathrooms?\b",
    "SQFT": r"\b[\d,]+\s+square feet\b",
}

for label, pattern in patterns.items():
    for match in re.finditer(pattern, text, re.IGNORECASE):
        entities.append(
            [match.start(), match.end(), label]
        )

# Use taxonomy matches as annotation candidates
amenities = extractor.load_taxonomy()

candidates = []
for amenity in amenities:
    pattern = r"(?<!\w)" + re.escape(amenity) + r"(?!\w)"

    for match in re.finditer(pattern, text, re.IGNORECASE):
        candidates.append(
            [match.start(), match.end(), "AMENITY"]
        )

# Prefer longer spans when taxonomy terms overlap
candidates.sort(key=lambda x: (-(x[1] - x[0]), x[0]))

accepted = []
for candidate in candidates:
    start, end, _ = candidate

    if not any(
        start < other[1] and end > other[0]
        for other in accepted
    ):
        accepted.append(candidate)

entities.extend(accepted)
entities.sort(key=lambda x: (x[0], x[1]))

print("ANNOTATION CANDIDATES:\n")
for start, end, label in entities:
    print(f"{label:10} [{start:4}, {end:4}]  {text[start:end]}")

print(f"\nTotal candidates: {len(entities)}")
print("Candidates were not saved. Review them with interactive_annotator.py.")
