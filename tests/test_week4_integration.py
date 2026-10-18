import os
from pathlib import Path

import pytest

from scripts.query_parser import QueryParser, load_valid_cities
from scripts.schema_validator import SchemaValidator
from scripts.sql_generator import SQLGenerator


def _first_configured_value(*names):
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            return value
    return None


def test_query_parser_to_read_only_mysql_select():
    city_file = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "processed"
        / "valid_cities.txt"
    )
    valid_cities = load_valid_cities(city_file)
    query = "Find 3+ bedroom homes in Irvine under $1.2m with a pool"

    filters = QueryParser(valid_cities=valid_cities).parse(query)
    assert filters.city == "Irvine"
    assert filters.bedrooms_min == 3
    assert filters.price_max == 1_200_000
    assert filters.pool is True
    assert SchemaValidator(valid_cities=valid_cities).validate(filters) == []

    sql, params = SQLGenerator(valid_cities=valid_cities).generate(filters)
    read_only_sql = sql + " LIMIT 10"  # Fixed limit; the generator remains unchanged.

    db_host = _first_configured_value("MYSQL_HOST", "DB_HOST") or "127.0.0.1"
    db_port = int(_first_configured_value("MYSQL_PORT", "DB_PORT") or "3306")
    db_user = _first_configured_value("MYSQL_USER", "DB_USER")
    db_password = _first_configured_value("MYSQL_PASSWORD", "DB_PASSWORD")
    missing_settings = [
        name
        for name, value in (
            ("MYSQL_USER/DB_USER", db_user),
            ("MYSQL_PASSWORD/DB_PASSWORD", db_password),
        )
        if value is None
    ]
    if missing_settings:
        pytest.skip(
            "MySQL integration unavailable: set " + " and ".join(missing_settings)
        )

    try:
        import mysql.connector
    except ImportError:
        pytest.skip("MySQL integration unavailable: mysql-connector-python is not installed")

    try:
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database="idx_exchange",
            connection_timeout=5,
        )
    except mysql.connector.Error:
        pytest.skip(
            "MySQL integration unavailable: could not connect to idx_exchange "
            "with the configured environment settings"
        )

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(read_only_sql, params)
        rows = cursor.fetchall()
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            connection.close()

    assert len(rows) <= 10
    for row in rows:
        assert row["L_City"].casefold() == filters.city.casefold()
        assert row["L_SystemPrice"] is not None
        assert row["L_SystemPrice"] <= filters.price_max
        assert row["L_Keyword2"] is not None
        assert row["L_Keyword2"] >= filters.bedrooms_min
        assert str(row["PoolPrivateYN"]) == "1"
