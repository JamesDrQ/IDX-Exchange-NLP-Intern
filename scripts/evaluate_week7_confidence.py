import pandas as pd

path = "data/processed/week7_test_predictions.csv"
df = pd.read_csv(path)

threshold = 0.60

df["correct"] = (
    df["intent"] == df["predicted_intent"]
)

df["low_confidence"] = df["confidence"] < threshold

print("=== WEEK 7 CONFIDENCE ANALYSIS ===")

print("\nTotal predictions:", len(df))
print("Overall accuracy:", round(df["correct"].mean(), 4))

print("\nConfidence summary:")
print(df["confidence"].describe().round(4))

low = df[df["low_confidence"]]
high = df[~df["low_confidence"]]

print(f"\nLow confidence (< {threshold}):", len(low))
print(f"High confidence (>= {threshold}):", len(high))

if len(high) > 0:
    print("High-confidence accuracy:",
          round(high["correct"].mean(), 4))

print("\nLow-confidence queries:")
print(low[
    ["query", "intent", "predicted_intent",
     "confidence", "correct"]
].sort_values("confidence").to_string(index=False))

print("\nPerformance by data source:")
print(
    df.groupby("source")
    .agg(
        count=("correct", "size"),
        accuracy=("correct", "mean"),
        mean_confidence=("confidence", "mean"),
    )
    .round(4)
    .to_string()
)
