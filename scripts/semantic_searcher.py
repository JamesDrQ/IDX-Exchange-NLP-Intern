from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]


class SemanticSearcher:
    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        self.df = pd.read_csv(
            ROOT / "data/processed/week5_listings.csv",
            dtype={"L_ListingID": str}
        )

        self.index = None

    def build_index(self):
        embeddings = np.load(
            ROOT / "data/models/week5_embeddings.npy"
        ).astype(np.float32)

        if len(embeddings) != len(self.df):
            raise ValueError("Listing count mismatch")

        embeddings = np.ascontiguousarray(embeddings)
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

        faiss.write_index(
            self.index,
            str(ROOT / "data/models/week5_faiss.index")
        )

    def load_index(self):
        self.index = faiss.read_index(
            str(ROOT / "data/models/week5_faiss.index")
        )

        if self.index.ntotal != len(self.df):
            raise ValueError("Index and CSV size mismatch")

    def search(self, query, top_k=5):
        if self.index is None:
            raise RuntimeError("Index not loaded")

        if not query.strip() or top_k < 1:
            raise ValueError("Invalid search query or top_k")

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        ).astype(np.float32)

        scores, indices = self.index.search(
            query_embedding,
            min(top_k, self.index.ntotal)
        )

        results = []

        for idx, score in zip(indices[0], scores[0]):
            if idx < 0:
                continue

            listing = self.df.iloc[int(idx)]

            results.append({
                "listing_id": listing["L_ListingID"],
                "remarks": listing["remarks"],
                "similarity": float(score)
            })

        return results


if __name__ == "__main__":
    searcher = SemanticSearcher()

    searcher.load_index()

    results = searcher.search(
        "modern home with a swimming pool",
        top_k=5
    )

    for i, result in enumerate(results, 1):
        print(f"\nRank {i}")
        print(f"Listing ID: {result['listing_id']}")
        print(f"Similarity: {result['similarity']:.4f}")
        print(f"Remarks: {result['remarks'][:200]}")
