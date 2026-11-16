import pandas as pd
import joblib

from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# Load labeled data
df = pd.read_csv(
    "data/processed/week7_intent_labeled.csv"
)

# Reproduce original 80/20 split
train_idx, test_idx = train_test_split(
    df.index,
    test_size=0.2,
    random_state=42,
    stratify=df["intent"],
)

train = df.loc[train_idx]
test = df.loc[test_idx].copy()

# Hybrid model
model = Pipeline([
    ("features", FeatureUnion([
        ("word", TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )),
        ("char", TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
        )),
    ])),
    ("classifier", LogisticRegression(
        max_iter=2000,
        random_state=42,
    )),
])

# Train only on original training set
model.fit(train["query"], train["intent"])

# Evaluate on original holdout
predictions = model.predict(test["query"])
probabilities = model.predict_proba(test["query"])

accuracy = accuracy_score(test["intent"], predictions)
macro_f1 = f1_score(
    test["intent"],
    predictions,
    average="macro",
)

print("=== WEEK 7 HYBRID EVALUATION ===")
print("Training samples:", len(train))
print("Testing samples:", len(test))
print(f"Accuracy: {accuracy:.4f}")
print(f"Macro F1: {macro_f1:.4f}")

print("\nClassification Report:")
print(classification_report(
    test["intent"],
    predictions,
    zero_division=0,
))

labels = model.classes_

cm = pd.DataFrame(
    confusion_matrix(
        test["intent"],
        predictions,
        labels=labels,
    ),
    index=labels,
    columns=labels,
)

print("\nConfusion Matrix:")
print(cm.to_string())

# Save model separately from baseline
Path("data/models").mkdir(
    parents=True,
    exist_ok=True,
)

model_path = (
    "data/models/week7_intent_classifier_hybrid.joblib"
)
joblib.dump(model, model_path)

# Save predictions
test["predicted_intent"] = predictions
test["confidence"] = probabilities.max(axis=1)
test["correct"] = (
    test["intent"] == test["predicted_intent"]
)

output = (
    "data/processed/week7_hybrid_test_predictions.csv"
)
test.to_csv(output, index=False)

print("\nMisclassified queries:")
errors = test[~test["correct"]]

if errors.empty:
    print("None")
else:
    print(errors[
        ["query", "intent", "predicted_intent", "confidence"]
    ].to_string(index=False))

print("\nModel saved:", model_path)
print("Predictions saved:", output)
