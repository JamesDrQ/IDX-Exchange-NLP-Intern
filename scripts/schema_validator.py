from math import isfinite
from numbers import Real
from typing import Iterable, Optional

from scripts.query_parser import PropertyFilters


class SchemaValidator:
    """Validate structured property filters without changing their values."""

    def __init__(self, valid_cities: Optional[Iterable[str]] = None) -> None:
        self._valid_cities = (
            None
            if valid_cities is None
            else {
                city.strip().casefold()
                for city in valid_cities
                if isinstance(city, str) and city.strip()
            }
        )

    def validate(self, filters: PropertyFilters) -> list[str]:
        errors = []
        valid_integer_fields = set()
        valid_number_fields = set()

        for field_name in (
            "price_min",
            "price_max",
            "bedrooms_min",
            "bedrooms_max",
        ):
            value = getattr(filters, field_name)
            if value is None:
                continue
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                valid_integer_fields.add(field_name)
            else:
                errors.append(f"{field_name} must be a non-negative integer")

        for field_name in ("bathrooms_min", "bathrooms_max"):
            value = getattr(filters, field_name)
            if value is None:
                continue
            valid_number = False
            if isinstance(value, int) and not isinstance(value, bool):
                valid_number = value >= 0
            elif isinstance(value, Real) and not isinstance(value, bool):
                valid_number = isfinite(value) and value >= 0

            if valid_number:
                valid_number_fields.add(field_name)
            else:
                errors.append(f"{field_name} must be a non-negative number")

        self._validate_range(
            filters.price_min,
            filters.price_max,
            "price_min",
            "price_max",
            valid_integer_fields,
            errors,
        )
        self._validate_range(
            filters.bedrooms_min,
            filters.bedrooms_max,
            "bedrooms_min",
            "bedrooms_max",
            valid_integer_fields,
            errors,
        )
        self._validate_range(
            filters.bathrooms_min,
            filters.bathrooms_max,
            "bathrooms_min",
            "bathrooms_max",
            valid_number_fields,
            errors,
        )

        if filters.city is not None:
            if not isinstance(filters.city, str):
                errors.append("city must be a string or None")
            elif (
                self._valid_cities is not None
                and filters.city.strip().casefold() not in self._valid_cities
            ):
                errors.append("city must match a configured valid city")

        if (
            filters.pool is not None
            and filters.pool is not True
            and filters.pool is not False
        ):
            errors.append("pool must be True, False, or None")

        return errors

    @staticmethod
    def _validate_range(
        minimum: object,
        maximum: object,
        minimum_name: str,
        maximum_name: str,
        valid_fields: set[str],
        errors: list[str],
    ) -> None:
        if (
            minimum is not None
            and maximum is not None
            and minimum_name in valid_fields
            and maximum_name in valid_fields
            and minimum > maximum
        ):
            errors.append(
                f"{minimum_name} must be less than or equal to {maximum_name}"
            )
