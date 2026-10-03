import os
import sys
import json
import pandas as pd

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from scripts.text_cleaning import TextCleaner


INPUT_PATH = "data/processed/listing_sample.csv"
CLEANED_PATH = "data/processed/listing_sample_cleaned.csv"
PROFILE_PATH = "data/processed/week2_profile.json"
EXAMPLES_PATH = "data/processed/week2_examples.csv"


def main():
    df = pd.read_csv(INPUT_PATH)

    cleaner = TextCleaner()

    # Generate profiling report
    profile = cleaner.profile_column(df, "remarks")

    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    # Clean remarks
    df["remarks_cleaned"] = (
        df["remarks"]
        .fillna("")
        .apply(cleaner.clean_text)
    )

    df.to_csv(
        CLEANED_PATH,
        index=False
    )

    # Save before/after examples
    examples = df[
        ["L_ListingID", "remarks", "remarks_cleaned"]
    ].head(20)

    examples.to_csv(
        EXAMPLES_PATH,
        index=False
    )

    print("Week 2 processing complete.")
    print(f"Cleaned dataset: {CLEANED_PATH}")
    print(f"Profiling report: {PROFILE_PATH}")
    print(f"Examples: {EXAMPLES_PATH}")
    print()
    print("Dataset shape:", df.shape)
    print()
    print("Profile:")
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()