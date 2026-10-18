import pytest

from scripts.query_parser import PropertyFilters
from scripts.schema_validator import SchemaValidator


def test_empty_filters_are_valid():
    assert SchemaValidator().validate(PropertyFilters()) == []


def test_valid_filter_values_and_boundary_ranges():
    filters = PropertyFilters(
        city="Irvine",
        price_min=0,
        price_max=0,
        bedrooms_min=0,
        bedrooms_max=0,
        bathrooms_min=0.0,
        bathrooms_max=0.0,
        pool=False,
    )

    assert SchemaValidator(valid_cities=["Irvine"]).validate(filters) == []


def test_city_validation_is_case_insensitive_and_does_not_modify_filters():
    filters = PropertyFilters(city="  iRvInE  ")

    assert SchemaValidator(valid_cities=["Irvine"]).validate(filters) == []
    assert filters.city == "  iRvInE  "


def test_city_is_not_checked_when_no_valid_city_list_is_provided():
    assert SchemaValidator().validate(PropertyFilters(city="Atlantis")) == []


@pytest.mark.parametrize("pool", [True, False, None])
def test_allowed_pool_values(pool):
    assert SchemaValidator().validate(PropertyFilters(pool=pool)) == []


@pytest.mark.parametrize(
    ("filters", "expected_error"),
    [
        (PropertyFilters(price_min=-1), "price_min must be a non-negative integer"),
        (PropertyFilters(price_max=1.5), "price_max must be a non-negative integer"),
        (PropertyFilters(price_min=True), "price_min must be a non-negative integer"),
        (PropertyFilters(bedrooms_min=-1), "bedrooms_min must be a non-negative integer"),
        (PropertyFilters(bedrooms_max=2.0), "bedrooms_max must be a non-negative integer"),
        (PropertyFilters(bathrooms_min=-0.5), "bathrooms_min must be a non-negative number"),
        (PropertyFilters(bathrooms_max="2"), "bathrooms_max must be a non-negative number"),
        (PropertyFilters(bathrooms_min=True), "bathrooms_min must be a non-negative number"),
        (PropertyFilters(bathrooms_max=float("nan")), "bathrooms_max must be a non-negative number"),
        (PropertyFilters(bathrooms_max=float("inf")), "bathrooms_max must be a non-negative number"),
        (PropertyFilters(city="Atlantis"), "city must match a configured valid city"),
        (PropertyFilters(pool=1), "pool must be True, False, or None"),
        (PropertyFilters(pool="false"), "pool must be True, False, or None"),
    ],
)
def test_invalid_fields_return_field_specific_errors(filters, expected_error):
    errors = SchemaValidator(valid_cities=["Irvine"]).validate(filters)

    assert expected_error in errors


@pytest.mark.parametrize(
    ("filters", "expected_error"),
    [
        (
            PropertyFilters(price_min=101, price_max=100),
            "price_min must be less than or equal to price_max",
        ),
        (
            PropertyFilters(bedrooms_min=4, bedrooms_max=3),
            "bedrooms_min must be less than or equal to bedrooms_max",
        ),
        (
            PropertyFilters(bathrooms_min=2.5, bathrooms_max=2),
            "bathrooms_min must be less than or equal to bathrooms_max",
        ),
    ],
)
def test_minimum_cannot_exceed_maximum(filters, expected_error):
    assert expected_error in SchemaValidator().validate(filters)


def test_invalid_values_are_not_modified():
    filters = PropertyFilters(price_min=-500, bedrooms_max=2.5, pool=0)
    before = (filters.price_min, filters.bedrooms_max, filters.pool)

    errors = SchemaValidator().validate(filters)

    assert len(errors) == 3
    assert (filters.price_min, filters.bedrooms_max, filters.pool) == before


def test_ranges_with_invalid_values_report_fields_without_comparing_them():
    filters = PropertyFilters(price_min="low", price_max=100)

    errors = SchemaValidator().validate(filters)

    assert errors == ["price_min must be a non-negative integer"]
