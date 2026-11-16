from pathlib import Path

import joblib
import numpy as np


class QueryIntentClassifier:
    """Classify real estate search intent."""

    def __init__(
        self,
        model_path="data/models/week7_intent_classifier_hybrid.joblib",
        confidence_threshold=0.60,
    ):
        if not 0 <= confidence_threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")

        if not Path(model_path).is_file():
            raise FileNotFoundError(model_path)

        self.model = joblib.load(model_path)
        self.threshold = confidence_threshold
        self.labels = list(self.model.classes_)

    def predict(self, query):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string")

        probabilities = self.model.predict_proba(
            [query.strip()]
        )[0]

        best_index = int(np.argmax(probabilities))

        intent = self.labels[best_index]
        confidence = float(probabilities[best_index])

        return {
            "query": query,
            "intent": intent,
            "confidence": confidence,
            "low_confidence": confidence < self.threshold,
            "probabilities": {
                label: float(prob)
                for label, prob in zip(
                    self.labels, probabilities
                )
            },
        }
