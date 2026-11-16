import pytest

from scripts.query_intent_classifier import QueryIntentClassifier


LABELS = {
    "browsing",
    "researching",
    "high_intent_inquiry",
}


@pytest.fixture(scope="module")
def classifier():
    return QueryIntentClassifier()


def test_model_labels(classifier):
    assert set(classifier.labels) == LABELS


def test_prediction_structure(classifier):
    result = classifier.predict(
        "Show me condos in San Diego"
    )

    assert result["intent"] in LABELS
    assert 0 <= result["confidence"] <= 1
    assert isinstance(result["low_confidence"], bool)
    assert set(result["probabilities"]) == LABELS


def test_probabilities_sum_to_one(classifier):
    result = classifier.predict(
        "Compare property taxes across neighborhoods"
    )

    total = sum(result["probabilities"].values())

    assert total == pytest.approx(1.0)


def test_confidence_matches_prediction(classifier):
    result = classifier.predict(
        "Schedule a home showing tomorrow"
    )

    predicted = result["intent"]

    assert result["confidence"] == pytest.approx(
        result["probabilities"][predicted]
    )


def test_low_confidence_flag(classifier):
    result = classifier.predict(
        "Find houses with a swimming pool"
    )

    assert result["low_confidence"] == (
        result["confidence"] < classifier.threshold
    )


@pytest.mark.parametrize("query", [
    "",
    "   ",
    None,
    123,
])
def test_invalid_queries(classifier, query):
    with pytest.raises(ValueError):
        classifier.predict(query)


@pytest.mark.parametrize("threshold", [
    -0.1,
    1.1,
])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError):
        QueryIntentClassifier(
            confidence_threshold=threshold
        )


def test_missing_model():
    with pytest.raises(FileNotFoundError):
        QueryIntentClassifier(
            model_path="nonexistent_model.joblib"
        )


def test_baseline_still_available():
    baseline = QueryIntentClassifier(
        model_path=(
            "data/models/"
            "week7_intent_classifier.joblib"
        )
    )

    result = baseline.predict("Find homes in Irvine")

    assert result["intent"] in LABELS
