import pandas as pd

df = pd.read_csv("data/processed/taxonomy_candidates.csv")

# Get rid of some obviously meaningless candidates.
bad_terms = {
    "the home",
    "this home",
    "one of",
    "welcome to",
    "features a",
    "home offers",
    "offers a",
    "a spacious",
    "opportunity to",
    "the property",
    "a large",
    "the perfect",
    "home is",
    "perfect for",
    "the main",
    "plenty of",
    "a rare",
    "ideal for",
    "space for",
    "the primary",
    "this property",
    "in one",
}

df = df[~df["term"].isin(bad_terms)].copy()

# Add manual approval.
df["keep"] = ""
df["category"] = ""
df["notes"] = ""

df.to_csv(
    "data/processed/taxonomy_review.csv",
    index=False
)

print(f"Saved {len(df)} terms for review")