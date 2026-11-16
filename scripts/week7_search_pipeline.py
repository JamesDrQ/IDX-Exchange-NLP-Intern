from dataclasses import asdict, is_dataclass
from pathlib import Path

from scripts.query_parser import (
    QueryParser,
    load_valid_cities,
)
from scripts.query_intent_classifier import QueryIntentClassifier


ROOT = Path(__file__).resolve().parents[1]


class Week7SearchPipeline:
    """Combine Week 4 query parsing and Week 7 intent classification."""

    def __init__(self):
        # Week 4: Load valid city names
        city_file = ROOT / "data/processed/valid_cities.txt"
        valid_cities = load_valid_cities(city_file)

        self.parser = QueryParser(valid_cities=valid_cities)

        # Week 7: Load trained Hybrid classifier
        model_path = (
            ROOT / "data/models/"
            "week7_intent_classifier_hybrid.joblib"
        )

        self.classifier = QueryIntentClassifier(
            model_path=str(model_path)
        )

    def analyze(self, query: str) -> dict:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string")

        # Extract structured property filters
        filters = self.parser.parse(query)

        # Predict search intent
        prediction = self.classifier.predict(query)

        # Convert PropertyFilters to a dictionary
        if is_dataclass(filters):
            filter_dict = asdict(filters)
        elif hasattr(filters, "model_dump"):
            filter_dict = filters.model_dump()
        else:
            filter_dict = vars(filters).copy()

        return {
            "query": query,
            "filters": filter_dict,
            "intent": prediction["intent"],
            "confidence": prediction["confidence"],
            "low_confidence": prediction["low_confidence"],
            "probabilities": prediction["probabilities"],
        }
