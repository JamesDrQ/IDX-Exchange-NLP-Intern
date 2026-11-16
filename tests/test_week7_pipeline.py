import pytest

from scripts.week7_search_pipeline import Week7SearchPipeline


LABELS = {
    "browsing",
    "researching",
    "high_intent_inquiry",
}


@pytest.fixture(scope="module")
def pipeline():
    return Week7SearchPipeline()


def test_pipeline_structure(pipeline):
    result = pipeline.analyze(
        "Show me homes in Irvine"
    )

    assert "query" in result
    assert "filters" in result
    assert "intent" in result
    assert "confidence" in result
    assert "low_confidence" in result
    assert "probabilities" in result


def test_property_filters(pipeline):
    query = (
        "Find 3+ bedroom homes in Irvine "
        "under $1.2m with a pool"
    )

    result = pipeline.analyze(query)
    filters = result["filters"]

    assert filters["city"] == "Irvine"
    assert filters["bedrooms_min"] == 3
    assert filters["price_max"] == 1_200_000
    assert filters["pool"] is True
    assert result["intent"] == "browsing"


def test_researching_intent(pipeline):
    result = pipeline.analyze(
        "Compare property taxes in Irvine and San Diego"
    )

    assert result["intent"] == "researching"


def test_high_intent(pipeline):
    result = pipeline.analyze(
        "Schedule a home tour tomorrow"
    )

    assert result["intent"] == "high_intent_inquiry"


def test_probabilities(pipeline):
    result = pipeline.analyze(
        "Find houses in San Diego"
    )

    probabilities = result["probabilities"]

    assert set(probabilities) == LABELS
    assert sum(probabilities.values()) == pytest.approx(1.0)
    assert result["confidence"] == pytest.approx(
        probabilities[result["intent"]]
    )


def test_confidence_flag(pipeline):
    result = pipeline.analyze(
        "Schedule a home tour tomorrow"
    )

    assert result["low_confidence"] == (
        result["confidence"] < pipeline.classifier.threshold
    )


@pytest.mark.parametrize("query", [
    "",
    "   ",
    None,
    123,
])
def test_invalid_queries(pipeline, query):
    with pytest.raises(ValueError):
        pipeline.analyze(query)
