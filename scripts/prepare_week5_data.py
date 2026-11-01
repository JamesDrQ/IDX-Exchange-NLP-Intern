
import pandas as pd
from pathlib import Path

output = Path("data/processed/week5_listings.csv")
if output.exists():
    raise FileExistsError(f"Refusing to overwrite existing Week 5 listings: {output}")

# Load Week 1 dataset
df = pd.read_csv("data/processed/listing_sample.csv")

# Keep listing IDs and descriptions
df = df[["L_ListingID", "remarks"]].copy()

# Remove missing or empty remarks
df = df.dropna(subset=["L_ListingID", "remarks"])
df["remarks"] = df["remarks"].astype(str).str.strip()
df = df[df["remarks"] != ""]

# Remove duplicate listing IDs
df = df.drop_duplicates(subset=["L_ListingID"])

# Save Week 5 dataset
output.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output, index=False)

print(f"Loaded {len(df)} listings")
print(df.head())
print(f"Saved to {output}")
