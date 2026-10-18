
import json
import pandas as pd
from pathlib import Path

input_path = Path("data/labeled/week3_annotation_sample.csv")
output_path = Path("data/labeled/week3_annotations.jsonl")

df = pd.read_csv(input_path)

# Do not overwrite existing annotations
if output_path.exists():
    raise FileExistsError(
        f"{output_path} already exists. "
        "Rename or back up the file before regenerating."
    )

with output_path.open("w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        record = {
            "source_row": int(row["source_row"]),
            "listing_id": str(row["L_ListingID"]),
            "text": row["remarks_cleaned"]
            if pd.notna(row["remarks_cleaned"]) else "",
            "entities": [],
            "annotated": False,
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"Created {len(df)} annotation records")
print(f"Saved to {output_path}")
