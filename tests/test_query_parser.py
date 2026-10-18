from pathlib import Path

import pytest

from scripts.query_parser import QueryParser, load_valid_cities


@pytest.mark.parametrize(
    ("text", "price_min", "price_max"),
    [
        ("under $700k", None, 700_000),
        ("below $1.2m", None, 1_200_000),
        ("less than $800,000", None, 800_000),
        ("over $500k", 500_000, None),
        ("above $600k", 600_000, None),
        ("between $500k and $900k", 500_000, 900_000),
    ],
)
def test_parse_price_examples(text, price_min, price_max):
    filters = QueryParser().parse(text)

    assert filters.price_min == price_min
    assert filters.price_max == price_max


def test_parse_query_without_price():
    filters = QueryParser().parse("Looking for a home in Oakland")

    assert filters.price_min is None
    assert filters.price_max is None


@pytest.mark.parametrize(
    ("text", "price_min", "price_max"),
    [
        ("under 700k", None, 700_000),
        ("above 1.2 million", 1_200_000, None),
        ("under 3 bedrooms", None, None),
        ("over 2 bathrooms", None, None),
    ],
)
def test_price_indicators_and_count_regressions(text, price_min, price_max):
    filters = QueryParser().parse(text)

    assert filters.price_min == price_min
    assert filters.price_max == price_max


@pytest.mark.parametrize(
    ("text", "bedrooms_min", "bedrooms_max"),
    [
        ("3 bedrooms", 3, 3),
        ("3 bed", 3, 3),
        ("3+ bedrooms", 3, None),
        ("at least 3 bedrooms", 3, None),
        ("minimum 3 beds", 3, None),
        ("up to 4 bedrooms", None, 4),
        ("no more than 4 beds", None, 4),
        ("between 2 and 4 bedrooms", 2, 4),
    ],
)
def test_parse_bedroom_count_examples(text, bedrooms_min, bedrooms_max):
    filters = QueryParser().parse(text)

    assert filters.bedrooms_min == bedrooms_min
    assert filters.bedrooms_max == bedrooms_max


@pytest.mark.parametrize(
    "text",
    [
        "Looking for a home in Oakland",
        "Sleeps 3 people and has 2 bathrooms",
        "under $700k",
        "over $2 million",
    ],
)
def test_queries_without_bedroom_counts_leave_bedroom_filters_empty(text):
    filters = QueryParser().parse(text)

    assert filters.bedrooms_min is None
    assert filters.bedrooms_max is None


def test_price_amount_is_not_interpreted_as_bedroom_count():
    filters = QueryParser().parse("under $700k")

    assert filters.price_max == 700_000
    assert filters.bedrooms_min is None
    assert filters.bedrooms_max is None


def test_combined_bedroom_and_price_query():
    filters = QueryParser().parse("3+ beds under $700k")

    assert filters.bedrooms_min == 3
    assert filters.bedrooms_max is None
    assert filters.price_min is None
    assert filters.price_max == 700_000


@pytest.mark.parametrize(
    ("text", "bathrooms_min", "bathrooms_max"),
    [
        ("2 bathrooms", 2.0, 2.0),
        ("2.5 baths", 2.5, 2.5),
        ("2+ bathrooms", 2.0, None),
        ("at least 2 baths", 2.0, None),
        ("minimum 1.5 bathrooms", 1.5, None),
        ("up to 3 bathrooms", None, 3.0),
        ("no more than 2.5 baths", None, 2.5),
        ("between 2 and 3.5 bathrooms", 2.0, 3.5),
        ("AT LEAST 2 BATHS", 2.0, None),
    ],
)
def test_parse_bathroom_count_examples(text, bathrooms_min, bathrooms_max):
    filters = QueryParser().parse(text)

    assert filters.bathrooms_min == bathrooms_min
    assert filters.bathrooms_max == bathrooms_max


@pytest.mark.parametrize(
    "text",
    [
        "Looking for a home in Oakland",
        "3 bedrooms",
        "3+ beds under $700k",
        "under $700k",
        "over $2 million",
    ],
)
def test_queries_without_bathroom_counts_leave_bathroom_filters_empty(text):
    filters = QueryParser().parse(text)

    assert filters.bathrooms_min is None
    assert filters.bathrooms_max is None


def test_combined_bedroom_bathroom_and_price_query():
    filters = QueryParser().parse("3+ beds, 2+ baths under $700k")

    assert filters.bedrooms_min == 3
    assert filters.bedrooms_max is None
    assert filters.bathrooms_min == 2.0
    assert filters.bathrooms_max is None
    assert filters.price_min is None
    assert filters.price_max == 700_000


def test_price_amount_is_not_interpreted_as_bathroom_count():
    filters = QueryParser().parse("under $700k")

    assert filters.price_max == 700_000
    assert filters.bathrooms_min is None
    assert filters.bathrooms_max is None


@pytest.mark.parametrize(
    ("text", "expected_city"),
    [
        ("homes in Irvine", "Irvine"),
        ("properties in San Diego", "San Diego"),
        ("properties in sAN dIEGO", "San Diego"),
        ("looking for a condo in Los Angeles", "Los Angeles"),
        ("irvine homes under $700k", "Irvine"),
    ],
)
def test_parse_configured_cities(text, expected_city):
    parser = QueryParser(
        valid_cities=["Irvine", "San Diego", "Los Angeles", "New York", "York"]
    )

    assert parser.parse(text).city == expected_city


def test_city_matching_prefers_full_city_name_over_partial_match():
    parser = QueryParser(valid_cities=["York", "New York"])

    assert parser.parse("homes in New York").city == "New York"
    assert parser.parse("homes in York").city == "York"


@pytest.mark.parametrize(
    "text",
    [
        "homes in Atlantis",
        "looking for a condo in Irvine",
    ],
)
def test_city_matching_uses_only_configured_cities(text):
    parser = QueryParser(valid_cities=["San Diego", "Los Angeles"])

    assert parser.parse(text).city is None


def test_city_matching_ignores_empty_city_values():
    parser = QueryParser(valid_cities=["", "   ", "Irvine"])

    assert parser.parse("homes in Irvine").city == "Irvine"


def test_combined_city_price_bedroom_and_bathroom_query():
    parser = QueryParser(valid_cities=["Irvine"])
    filters = parser.parse("Irvine homes with 3+ beds, 2+ baths under $700k with a pool")

    assert filters.city == "Irvine"
    assert filters.bedrooms_min == 3
    assert filters.bedrooms_max is None
    assert filters.bathrooms_min == 2.0
    assert filters.bathrooms_max is None
    assert filters.price_min is None
    assert filters.price_max == 700_000
    assert filters.pool is True


def test_load_valid_cities_strips_whitespace_and_ignores_empty_lines(tmp_path):
    city_file = tmp_path / "valid_cities.txt"
    city_file.write_text(
        " Irvine \n\n San Diego  \n   \nLos Angeles\n", encoding="utf-8"
    )

    assert load_valid_cities(city_file) == ["Irvine", "San Diego", "Los Angeles"]


def test_real_city_dictionary_supports_example_cities():
    city_file = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "processed"
        / "valid_cities.txt"
    )
    parser = QueryParser(valid_cities=load_valid_cities(city_file))

    assert parser.parse("homes in Irvine").city == "Irvine"
    assert parser.parse("properties in San Diego").city == "San Diego"
    assert parser.parse("looking for a condo in Los Angeles").city == "Los Angeles"


@pytest.mark.parametrize(
    "text",
    [
        "with a pool",
        "has a private pool",
        "homes with swimming pools",
        "pool required",
        "WITH A POOL",
    ],
)
def test_parse_positive_pool_preference(text):
    assert QueryParser().parse(text).pool is True


@pytest.mark.parametrize(
    "text",
    [
        "without a pool",
        "no swimming pool",
        "don't want a pool",
        "WITHOUT A POOL",
    ],
)
def test_parse_negative_pool_preference(text):
    assert QueryParser().parse(text).pool is False


@pytest.mark.parametrize(
    "text",
    [
        "Looking for a home",
        "a home with a large yard",
        "3 bedrooms under $700k",
    ],
)
def test_pool_preference_is_none_when_unspecified(text):
    assert QueryParser().parse(text).pool is None


def test_negative_pool_preference_takes_priority_over_positive_phrase():
    filters = QueryParser().parse("with a pool, but don't want a pool")

    assert filters.pool is False


def test_combined_query_with_negative_pool_preference():
    parser = QueryParser(valid_cities=["Irvine"])
    filters = parser.parse(
        "Irvine homes with 3+ beds, 2+ baths under $700k without a pool"
    )

    assert filters.city == "Irvine"
    assert filters.bedrooms_min == 3
    assert filters.bedrooms_max is None
    assert filters.bathrooms_min == 2.0
    assert filters.bathrooms_max is None
    assert filters.price_min is None
    assert filters.price_max == 700_000
    assert filters.pool is False


def test_parse_week4_regression_q41_private_pool_after_other_filters():
    parser = QueryParser(valid_cities=["Los Angeles"])
    filters = parser.parse(
        "Los Angeles condos with 2 bathrooms, a private pool, "
        "and a price above $600k"
    )

    assert filters.city == "Los Angeles"
    assert filters.bathrooms_min == 2.0
    assert filters.bathrooms_max == 2.0
    assert filters.price_min == 600_000
    assert filters.pool is True


def test_parse_week4_regression_q47_pool_in_and_phrase():
    parser = QueryParser(valid_cities=["Sunnyvale"])
    filters = parser.parse(
        "Find a Sunnyvale home with minimum 3 beds, 2+ baths, and a pool, "
        "below $1.5m"
    )

    assert filters.city == "Sunnyvale"
    assert filters.bedrooms_min == 3
    assert filters.bedrooms_max is None
    assert filters.bathrooms_min == 2.0
    assert filters.bathrooms_max is None
    assert filters.price_max == 1_500_000
    assert filters.pool is True
