import pandas as pd
import joblib

from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# 1. Load dataset
df = pd.read_csv(
    "data/processed/week7_intent_labeled.csv"
)

X = df["query"]
y = df["intent"]

# 2. Stratified train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)

# 3. TF-IDF + Logistic Regression pipeline
model = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2),
        sublinear_tf=True,
    )),
    ("classifier", LogisticRegression(
        max_iter=2000,
        random_state=42,
    )),
])

# 4. Train model
model.fit(X_train, y_train)

# 5. Evaluate model
y_pred = model.predict(X_test)
probabilities = model.predict_proba(X_test)
labels = model.classes_

accuracy = accuracy_score(y_test, y_pred)
macro_f1 = f1_score(
    y_test, y_pred, average="macro"
)

print("\n=== WEEK 7 MODEL EVALUATION ===")
print("Training samples:", len(X_train))
print("Testing samples:", len(X_test))
print(f"Accuracy: {accuracy:.4f}")
print(f"Macro F1: {macro_f1:.4f}")

print("\nClassification Report:")
print(classification_report(
    y_test,
    y_pred,
    zero_division=0,
))

cm = pd.DataFrame(
    confusion_matrix(y_test, y_pred, labels=labels),
    index=labels,
    columns=labels,
)

print("\nConfusion Matrix:")
print(cm.to_string())

# 6. Save model
Path("data/models").mkdir(
    parents=True, exist_ok=True
)

model_path = "data/models/week7_intent_classifier.joblib"
joblib.dump(model, model_path)

# 7. Save test predictions and confidence
results = df.loc[
    X_test.index, ["query", "intent", "source"]
].copy().reset_index(drop=True)

results["predicted_intent"] = y_pred
results["confidence"] = probabilities.max(axis=1)
results["correct"] = (
    results["intent"] == results["predicted_intent"]
)

for i, label in enumerate(labels):
    results[f"prob_{label}"] = probabilities[:, i]

output = "data/processed/week7_test_predictions.csv"
results.to_csv(output, index=False)

print("\nModel saved:", model_path)
print("Predictions saved:", output)

# 8. Error analysis
errors = results[~results["correct"]]

print("\nMisclassified queries:", len(errors))

if not errors.empty:
    print(errors[
        ["query", "intent", "predicted_intent", "confidence"]
    ].to_string(index=False))
