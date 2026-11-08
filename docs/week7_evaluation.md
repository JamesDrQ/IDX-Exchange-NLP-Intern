# Week 7 — Search Query Intent Classification

## 1. Objective

Build a supervised text classifier to categorize real estate
search queries into three intent classes:

- browsing
- researching
- high_intent_inquiry

The classifier predicts intent and returns class probabilities
and a low-confidence flag.

## 2. Dataset

Total labeled queries: 210

Class distribution:
- browsing: 73
- researching: 67
- high_intent_inquiry: 70

Data sources:
- Week 4 sample queries: 60
- Synthetic queries: 150

All 210 candidate labels were reviewed and approved.

Limitations:
- Synthetic queries are not real user search logs.
- All Week 4 queries belong to the browsing class.
- Source-specific language patterns may bias evaluation.
- Labels reflect linguistic intent, not verified buyer readiness.

## 3. Modeling Approach

Two supervised models were evaluated.

### Baseline
- Word-level TF-IDF
- Unigrams and bigrams
- Logistic Regression

### Hybrid
- Word-level TF-IDF (1-2 grams)
- Character-level TF-IDF (3-5 grams)
- Logistic Regression

Both models use scikit-learn Pipelines.

Data split:
- Training: 168 queries
- Holdout: 42 queries
- Stratified 80/20 split
- Random state: 42

TF-IDF features are fitted only on training data.

## 4. Cross-Validation Results

Five-fold stratified cross-validation on the
168 training queries:

| Metric | Baseline | Hybrid |
|---|---:|---:|
| Mean Accuracy | 0.9642 | 0.9761 |
| Mean Macro F1 | 0.9639 | 0.9762 |
| Macro F1 Std | 0.0118 | 0.0223 |

Hybrid achieved slightly higher cross-validation
scores, although variation across folds was higher.

## 5. Original Holdout Evaluation

| Metric | Baseline | Hybrid |
|---|---:|---:|
| Accuracy | 0.9524 | 0.9286 |
| Macro F1 | 0.9514 | 0.9277 |
| Errors | 2/42 | 3/42 |

Hybrid confusion matrix:

| Actual / Predicted | Browsing | High Intent | Researching |
|---|---:|---:|---:|
| Browsing | 14 | 0 | 1 |
| High Intent | 0 | 13 | 1 |
| Researching | 0 | 1 | 12 |

The baseline performed slightly better on this holdout.
The difference is only one prediction.

## 6. Additional Synthetic Stress Test

A separate set of 21 newly written synthetic queries
was used to diagnose behavior on alternative wording.

| Metric | Baseline | Hybrid |
|---|---:|---:|
| Accuracy | 0.7619 | 0.8095 |
| Macro F1 | 0.7532 | 0.8056 |
| Errors | 5/21 | 4/21 |

Hybrid performed better on this diagnostic set.

Remaining errors include:
- Casual browsing expressions classified as researching
- Market-trend questions classified as high intent
- Property appreciation questions classified as browsing

These findings suggest sensitivity to vocabulary and
query phrasing.

The stress test is small and synthetic.
It does not establish real-world performance.

## 7. Confidence Analysis

Baseline model on the original 42-query holdout:

- Mean confidence: 0.6425
- Experimental threshold: 0.60
- Low-confidence predictions: 14/42
- High-confidence predictions: 28/42
- High-confidence accuracy: 28/28
- Low-confidence accuracy: 12/14

The 0.60 threshold is a heuristic.

On the separate stress test, some incorrect predictions
exceeded 0.60 confidence. Therefore, confidence scores
should not be interpreted as calibrated probabilities.

The reported confidence summary applies to the baseline,
not the final Hybrid model.

## 8. Selected Model

Selected candidate: Hybrid Word + Character TF-IDF
with Logistic Regression.

Reasons:
- Higher mean cross-validation Macro F1
- Higher accuracy on the synthetic stress test
- Compatible with the existing prediction interface

The baseline is retained for comparison.

Important evaluation caveat:
The original holdout and the 21-query stress test were
examined during model development and selection.
Their results should be considered development
diagnostics rather than untouched final validation.

A fresh, representative evaluation dataset is needed
before claiming production-level generalization.

## 9. Implementation

Main components:
- QueryIntentClassifier
- Week7SearchPipeline
- Week 4 QueryParser integration

Classifier outputs:
- intent
- confidence
- low_confidence
- probabilities

Pipeline outputs:
- Structured property filters
- Predicted search intent
- Confidence information

The integration does not execute database searches.

The Week 4 Parser currently extracts a single city,
so multi-city comparison queries may lose information.

## 10. Testing

Week 7 unit and integration tests:
23 passed.

Full project regression suite:
266 passed, 1 warning.

The warning originates from the Week 3
test_manifest_path function returning a non-None value.

No failing tests were reported.

## 11. Limitations and Future Work

1. Collect real user queries with independently verified labels.
2. Evaluate on a fresh untouched test set.
3. Improve recognition of unfamiliar researching queries.
4. Study confidence calibration.
5. Expand multi-city parsing support.
6. Monitor model behavior on ambiguous queries.
7. Evaluate the complete search pipeline end-to-end.

## 12. Conclusion

Week 7 successfully implemented a three-class search
intent classifier with confidence scores.

The selected Hybrid model achieved:
- 92.86% accuracy on the original holdout
- 80.95% accuracy on the synthetic stress test
- 0.9762 mean Macro F1 in training-only cross-validation

The classifier was integrated with the Week 4
QueryParser, and all 266 project tests passed.

Performance on real-world user traffic remains unverified.
