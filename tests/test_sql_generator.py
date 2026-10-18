import pytest

from scripts.query_parser import PropertyFilters
from scripts.sql_generator import SQLGenerator, UnsupportedFilterError


def test_generate_select_with_no_filters():
    sql, params = SQLGenerator().generate(PropertyFilters())

    assert sql == "SELECT * FROM rets_property"
    assert params == []


@pytest.mark.parametrize(
    ("filters", "condition", "value"),
    [
        (PropertyFilters(city="Irvine"), "L_City = %s", "Irvine"),
        (PropertyFilters(price_min=500_000), "L_SystemPrice >= %s", 500_000),
        (PropertyFilters(price_max=900_000), "L_SystemPrice <= %s", 900_000),
        (PropertyFilters(bedrooms_min=2), "L_Keyword2 >= %s", 2),
        (PropertyFilters(bedrooms_max=4), "L_Keyword2 <= %s", 4),
        (PropertyFilters(bathrooms_min=1.5), "LM_Dec_3 >= %s", 1.5),
        (PropertyFilters(bathrooms_max=3.0), "LM_Dec_3 <= %s", 3.0),
        (PropertyFilters(pool=True), "PoolPrivateYN = %s", "1"),
    ],
)
def test_generate_individual_filter_conditions(filters, condition, value):
    sql, params = SQLGenerator().generate(filters)

    assert sql == f"SELECT * FROM rets_property WHERE {condition}"
    assert params == [value]


def test_generate_combined_filter_conditions_in_stable_order():
    filters = PropertyFilters(
        city="San Diego",
        price_min=500_000,
        price_max=900_000,
        bedrooms_min=2,
        bedrooms_max=4,
        bathrooms_min=1.5,
        bathrooms_max=3.0,
        pool=True,
    )

    sql, params = SQLGenerator().generate(filters)

    assert sql == (
        "SELECT * FROM rets_property WHERE L_City = %s"
        " AND L_SystemPrice >= %s AND L_SystemPrice <= %s"
        " AND L_Keyword2 >= %s AND L_Keyword2 <= %s"
        " AND LM_Dec_3 >= %s AND LM_Dec_3 <= %s"
        " AND PoolPrivateYN = %s"
    )
    assert params == ["San Diego", 500_000, 900_000, 2, 4, 1.5, 3.0, "1"]


@pytest.mark.parametrize(
    ("filters", "error_text"),
    [
        (PropertyFilters(price_min=-1), "price_min"),
        (PropertyFilters(bedrooms_min=2.5), "bedrooms_min"),
        (PropertyFilters(bathrooms_max=-0.5), "bathrooms_max"),
        (PropertyFilters(price_min=800_000, price_max=700_000), "price_min"),
    ],
)
def test_invalid_filters_are_rejected(filters, error_text):
    with pytest.raises(ValueError, match=error_text):
        SQLGenerator().generate(filters)


def test_configured_city_allowlist_is_validated():
    with pytest.raises(ValueError, match="city"):
        SQLGenerator(valid_cities=["Irvine"]).generate(
            PropertyFilters(city="Atlantis")
        )


def test_pool_false_is_rejected_as_unsupported():
    with pytest.raises(UnsupportedFilterError, match="pool=False is unsupported"):
        SQLGenerator().generate(PropertyFilters(pool=False))


def test_sql_injection_attempt_is_bound_as_a_parameter():
    attempted_city = "Irvine' OR '1'='1"

    sql, params = SQLGenerator().generate(PropertyFilters(city=attempted_city))

    assert sql == "SELECT * FROM rets_property WHERE L_City = %s"
    assert attempted_city not in sql
    assert params == [attempted_city]
