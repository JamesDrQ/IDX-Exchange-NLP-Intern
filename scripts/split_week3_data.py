
import json
import random
from pathlib import Path

DATA_DIR = Path("data/labeled")
INPUT_PATH = DATA_DIR / "week3_auto_labels.jsonl"
OUTPUT_PATH = DATA_DIR / "week3_split.json"

with INPUT_PATH.open(encoding="utf-8") as f:
    records = [json.loads(line) for line in f]

assert len(records) == 250

# Use fixed seed for reproducibility
rng = random.Random(42)

# First listing has already been manually reviewed,
# so exclude it from the held-out test set.
indices = list(range(1, len(records)))
rng.shuffle(indices)

development = [0] + indices[:29]
test = indices[29:59]
remaining = indices[59:]

split = {
    "development": development,
    "test": test,
    "remaining": remaining,
}

assert len(development) == 30
assert len(test) == 30
assert len(remaining) == 190
assert len(set(development + test + remaining)) == 250

# Avoid overwriting an existing split
with OUTPUT_PATH.open("x", encoding="utf-8") as f:
    json.dump(split, f, indent=2)

print("Development:", len(development))
print("Test:", len(test))
print("Remaining:", len(remaining))
print("Saved:", OUTPUT_PATH)
