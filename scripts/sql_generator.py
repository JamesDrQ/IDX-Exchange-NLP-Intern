from typing import Iterable, Optional

from scripts.query_parser import PropertyFilters
from scripts.schema_validator import SchemaValidator


class UnsupportedFilterError(ValueError):
    """Raised when a valid filter cannot be represented safely in SQL."""


class SQLGenerator:
    _TABLE = "rets_property"
    _FILTER_MAPPINGS = (
        ("city", "L_City", "="),
        ("price_min", "L_SystemPrice", ">="),
        ("price_max", "L_SystemPrice", "<="),
        ("bedrooms_min", "L_Keyword2", ">="),
        ("bedrooms_max", "L_Keyword2", "<="),
        ("bathrooms_min", "LM_Dec_3", ">="),
        ("bathrooms_max", "LM_Dec_3", "<="),
    )

    def __init__(self, valid_cities: Optional[Iterable[str]] = None) -> None:
        self._validator = SchemaValidator(valid_cities=valid_cities)

    def generate(self, filters: PropertyFilters) -> tuple[str, list[object]]:
        errors = self._validator.validate(filters)
        if errors:
            raise ValueError("Invalid filters: " + "; ".join(errors))

        if filters.pool is False:
            raise UnsupportedFilterError(
                "pool=False is unsupported: empty and NULL PoolPrivateYN values "
                "do not prove that a property has no pool"
            )

        conditions = []
        params = []
        for field_name, column_name, operator in self._FILTER_MAPPINGS:
            value = getattr(filters, field_name)
            if value is not None:
                conditions.append(f"{column_name} {operator} %s")
                params.append(value)

        if filters.pool is True:
            conditions.append("PoolPrivateYN = %s")
            params.append("1")

        sql = f"SELECT * FROM {self._TABLE}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        return sql, params
