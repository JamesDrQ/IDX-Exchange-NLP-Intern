from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

from scripts.query_intent_classifier import QueryIntentClassifier


# New, independently written synthetic queries.
# Keep these OUT of model training.
test_cases = [
    # Browsing
    ("Any bungalows with a basement around Escondido?", "browsing"),
    ("List condos with two parking spaces", "browsing"),
    ("I'm just looking at what's for sale in Del Mar", "browsing"),
    ("Show listings featuring vaulted ceilings and a sunroom", "browsing"),
    ("Are there small homes with an ADU in Chula Vista?", "browsing"),
    ("Pull up listings below 750k with three bathrooms", "browsing"),
    ("What duplexes are for sale in San Marcos?", "browsing"),

    # Researching
    ("Has the median sale-to-list ratio shifted since spring?", "researching"),
    ("Would a newer home cost less to heat than an older one?", "researching"),
    ("How does property tax assessment work after a purchase?", "researching"),
    ("What are the downsides of living next to power lines?", "researching"),
    ("What percentage of listings get price cuts before selling?", "researching"),
    ("Do homes with ADUs appreciate faster than similar homes?", "researching"),
    ("How can I calculate the break-even point for renting versus buying?", "researching"),

    # High intent
    ("Could you put me down for a tour at 10 am on Monday?", "high_intent_inquiry"),
    ("Please forward my offer letter to the seller's agent tonight", "high_intent_inquiry"),
    ("I want to sign the purchase agreement today", "high_intent_inquiry"),
    ("Can someone meet me at the property in an hour?", "high_intent_inquiry"),
    ("I'm ready to wire the deposit; please send escrow details", "high_intent_inquiry"),
    ("Set up a final walkthrough before closing this Friday", "high_intent_inquiry"),
    ("Please call the agent and arrange an appointment this evening", "high_intent_inquiry"),
]


def main():
    df = pd.DataFrame(test_cases, columns=["query", "intent"])

    # Ensure no exact overlap with existing labeled queries.
    training_data = pd.read_csv(
        "data/processed/week7_intent_labeled.csv"
    )

    existing = set(
        training_data["query"].str.strip().str.casefold()
    )
    new_queries = set(df["query"].str.strip().str.casefold())

    assert existing.isdisjoint(new_queries), (
        "Test queries overlap with existing dataset"
    )

    classifier = QueryIntentClassifier()

    predictions = [
        classifier.predict(query)
        for query in df["query"]
    ]

    df["predicted_intent"] = [
        result["intent"] for result in predictions
    ]
    df["confidence"] = [
        result["confidence"] for result in predictions
    ]
    df["low_confidence"] = [
        result["low_confidence"] for result in predictions
    ]
    df["correct"] = (
        df["intent"] == df["predicted_intent"]
    )
    df["source"] = "synthetic_stress_test"

    accuracy = accuracy_score(
        df["intent"], df["predicted_intent"]
    )
    macro_f1 = f1_score(
        df["intent"],
        df["predicted_intent"],
        average="macro",
    )

    print("=== WEEK 7 GENERALIZATION TEST ===")
    print("Total queries:", len(df))
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")

    print("\nClassification Report:")
    print(classification_report(
        df["intent"],
        df["predicted_intent"],
        zero_division=0,
    ))

    labels = classifier.labels
    cm = pd.DataFrame(
        confusion_matrix(
            df["intent"],
            df["predicted_intent"],
            labels=labels,
        ),
        index=labels,
        columns=labels,
    )

    print("\nConfusion Matrix:")
    print(cm.to_string())

    print("\nLow-confidence queries:",
          int(df["low_confidence"].sum()))

    print("\nIncorrect predictions:")
    errors = df[~df["correct"]]

    if errors.empty:
        print("None")
    else:
        print(errors[
            ["query", "intent", "predicted_intent", "confidence"]
        ].to_string(index=False))

    output = Path(
        "data/processed/week7_generalization_predictions.csv"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output, index=False)
    print("\nSaved:", output)


if __name__ == "__main__":
    main()
