
import pandas as pd
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

output = Path("data/models/week5_embeddings.npy")
if output.exists():
    raise FileExistsError(f"Refusing to overwrite existing embeddings: {output}")

# Load Week 5 listings
df = pd.read_csv("data/processed/week5_listings.csv")

remarks = df["remarks"].astype(str).tolist()

# Load pretrained embedding model
model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# Generate embeddings
embeddings = model.encode(
    remarks,
    batch_size=32,
    show_progress_bar=True,
    normalize_embeddings=True
)

embeddings = np.asarray(embeddings, dtype=np.float32)

# Save embeddings
output.parent.mkdir(parents=True, exist_ok=True)

np.save(output, embeddings)

print(f"Listings: {len(remarks)}")
print(f"Embeddings shape: {embeddings.shape}")
print(f"Saved to {output}")
