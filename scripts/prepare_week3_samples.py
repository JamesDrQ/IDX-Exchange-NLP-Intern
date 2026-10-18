
import pandas as pd

df = pd.read_csv(
    "data/processed/listing_sample_cleaned.csv"
)

# Reproducible random sampling
sample = df.sample(n=250, random_state=42).copy()

# Keep original row indices for traceability
sample.insert(0, "source_row", sample.index)

sample = sample[
    [
        "source_row",
        "L_ListingID",
        "remarks",
        "remarks_cleaned",
    ]
]

sample.to_csv(
    "data/labeled/week3_annotation_sample.csv",
    index=False,
)

print("Sample shape:", sample.shape)
print(sample.head(3)[["source_row", "L_ListingID"]])
