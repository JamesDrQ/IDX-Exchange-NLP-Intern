import pandas as pd

from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_validate,
)
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


# Load existing labeled dataset
df = pd.read_csv(
    "data/processed/week7_intent_labeled.csv"
)

# Reproduce original train/test split.
# Use training data ONLY for cross-validation.
X_train, X_test, y_train, y_test = train_test_split(
    df["query"],
    df["intent"],
    test_size=0.2,
    random_state=42,
    stratify=df["intent"],
)

# Model 1: Original baseline
baseline = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2),
        sublinear_tf=True,
    )),
    ("classifier", LogisticRegression(
        max_iter=2000,
        random_state=42,
    )),
])

# Model 2: Word + Character TF-IDF
hybrid = Pipeline([
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

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42,
)

models = {
    "Baseline Word TF-IDF": baseline,
    "Hybrid Word + Char TF-IDF": hybrid,
}

print("=== WEEK 7 MODEL COMPARISON ===")
print("Cross-validation samples:", len(X_train))
print("Original holdout excluded:", len(X_test))

for name, model in models.items():

    scores = cross_validate(
        model,
        X_train,
        y_train,
        cv=cv,
        scoring={
            "accuracy": "accuracy",
            "macro_f1": "f1_macro",
        },
        n_jobs=1,
    )

    print(f"\n{name}")
    print(
        "Mean Accuracy:",
        round(scores["test_accuracy"].mean(), 4)
    )
    print(
        "Mean Macro F1:",
        round(scores["test_macro_f1"].mean(), 4)
    )
    print(
        "F1 Std:",
        round(scores["test_macro_f1"].std(), 4)
    )
