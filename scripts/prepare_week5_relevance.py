import re
import numpy as np
import pandas as pd
from pathlib import Path
from rank_bm25 import BM25Okapi
from semantic_searcher import SemanticSearcher

output = Path("data/processed/week5_relevance.csv")
if output.exists():
    raise FileExistsError(f"Refusing to overwrite existing relevance labels: {output}")

# Five evaluation queries
queries = [
    "modern home with a swimming pool",
    "quiet neighborhood with mountain views",
    "spacious backyard for family gatherings",
    "renovated kitchen with a large island",
    "single story house with a three car garage"
]

# Load listings
df = pd.read_csv(
    "data/processed/week5_listings.csv",
    dtype={"L_ListingID": str}
)

def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())

# Build BM25
corpus = df["remarks"].astype(str).tolist()
tokenized = [tokenize(text) for text in corpus]
bm25 = BM25Okapi(tokenized)

# Load Semantic Search
semantic = SemanticSearcher()
semantic.load_index()

rows = []

for query in queries:
    # Semantic Search
    semantic_results = semantic.search(query, top_k=5)

    for rank, result in enumerate(semantic_results, 1):
        rows.append({
            "query": query,
            "method": "semantic",
            "rank": rank,
            "listing_id": result["listing_id"],
            "remarks": result["remarks"],
            "relevance": ""
        })

    # BM25 Search
    scores = bm25.get_scores(tokenize(query))
    top_indices = np.argsort(-scores)[:5]

    for rank, idx in enumerate(top_indices, 1):
        listing = df.iloc[int(idx)]
        rows.append({
            "query": query,
            "method": "bm25",
            "rank": rank,
            "listing_id": listing["L_ListingID"],
            "remarks": listing["remarks"],
            "relevance": ""
        })

# Save evaluation dataset
output.parent.mkdir(parents=True, exist_ok=True)

result_df = pd.DataFrame(rows)
result_df.to_csv(output, index=False)

print(f"Queries: {len(queries)}")
print(f"Evaluation pairs: {len(result_df)}")
print(f"Saved to {output}")
