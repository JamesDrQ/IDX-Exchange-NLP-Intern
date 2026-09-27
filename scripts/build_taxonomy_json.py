import json
import pandas as pd

df = pd.read_csv("data/processed/taxonomy_review.csv")

# Keep only terms that were manually approved
kept = df[df["keep"].astype(str).str.lower() == "yes"].copy()

terms = []

category_counts = {}

for _, row in kept.iterrows():
    category = row["category"]

    category_counts[category] = category_counts.get(category, 0) + 1

    term_id = f"{category}_{category_counts[category]:03d}"

    terms.append({
        "id": term_id,
        "term": row["term"],
        "category": category
    })

taxonomy = {
    "terms": terms
}

with open("data/processed/taxonomy.json", "w") as f:
    json.dump(taxonomy, f, indent=2)

print(f"Saved {len(terms)} terms to taxonomy.json")
print("Category counts:")

for category, count in sorted(category_counts.items()):
    print(f"  {category}: {count}")