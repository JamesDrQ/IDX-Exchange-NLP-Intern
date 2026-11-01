import faiss
import numpy as np
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Load existing listings and embeddings
df = pd.read_csv("data/processed/week5_listings.csv")
embeddings = np.load("data/models/week5_embeddings.npy")
embeddings = np.ascontiguousarray(
    embeddings, dtype=np.float32
)

assert len(df) == len(embeddings), "Data size mismatch"

# Build FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(embeddings)

# Save index
output = Path("data/models/week5_faiss.index")
if output.exists():
    raise FileExistsError(f"Refusing to overwrite existing FAISS index: {output}")
faiss.write_index(index, str(output))

print(f"Index dimension: {dimension}")
print(f"Indexed listings: {index.ntotal}")
print(f"Saved to {output}")

# Test semantic search
model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

query = "house with a swimming pool and large backyard"

query_embedding = model.encode(
    [query],
    normalize_embeddings=True
).astype(np.float32)

scores, indices = index.search(query_embedding, 5)

print(f"\nQuery: {query}")
print("\nTop 5 results:")

for rank, (idx, score) in enumerate(
    zip(indices[0], scores[0]), start=1
):
    listing = df.iloc[int(idx)]

    print(f"\nRank {rank}")
    print(f"Listing ID: {listing['L_ListingID']}")
    print(f"Similarity: {score:.4f}")
    print(f"Remarks: {listing['remarks'][:200]}...")
