"""Compare Week 5 BM25 and Semantic Search results for the evaluation queries."""

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LISTINGS_PATH = ROOT / "data/processed/week5_listings.csv"
QUERIES = [
    "modern home with a swimming pool",
    "quiet neighborhood with mountain views",
    "spacious backyard for family gatherings",
    "renovated kitchen with a large island",
    "single story house with a three car garage",
]


def tokenize(text: str) -> list[str]:
    """Lowercase tokenization shared by BM25 corpus and queries."""
    return re.findall(r"[a-z0-9]+", str(text).lower())


def build_bm25(df: pd.DataFrame):
    """Create a BM25 index over the listing remarks."""
    from rank_bm25 import BM25Okapi

    corpus = df["remarks"].fillna("").astype(str).tolist()
    return BM25Okapi([tokenize(text) for text in corpus])


def bm25_search(df: pd.DataFrame, bm25, query: str, top_k: int = 5) -> list[dict]:
    if not query.strip() or top_k < 1:
        raise ValueError("Invalid search query or top_k")
    if df.empty:
        return []
    scores = np.asarray(bm25.get_scores(tokenize(query)))
    indices = np.argsort(-scores, kind="stable")[: min(top_k, len(df))]
    return [
        {
            "listing_id": df.iloc[int(idx)]["L_ListingID"],
            "remarks": df.iloc[int(idx)]["remarks"],
            "score": float(scores[idx]),
        }
        for idx in indices
    ]


def main() -> None:
    from semantic_searcher import SemanticSearcher

    df = pd.read_csv(LISTINGS_PATH, dtype={"L_ListingID": str})
    bm25 = build_bm25(df)
    semantic = SemanticSearcher()
    semantic.load_index()

    query = QUERIES[0]
    for title, results, score_key in (
        ("SEMANTIC SEARCH", semantic.search(query, top_k=5), "similarity"),
        ("BM25", bm25_search(df, bm25, query, top_k=5), "score"),
    ):
        print(f"\n===== {title} =====")
        for rank, result in enumerate(results, 1):
            print(f"\nRank {rank}")
            print(f"Listing ID: {result['listing_id']}")
            print(f"Score: {result[score_key]:.4f}")
            print(f"Remarks: {result['remarks'][:200]}")


if __name__ == "__main__":
    main()
