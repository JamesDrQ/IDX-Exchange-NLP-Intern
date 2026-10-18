from dataclasses import asdict, dataclass
import re
from pathlib import Path
from typing import Iterable, Optional, Pattern, Union


@dataclass
class PropertyFilters:
    city: Optional[str] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    bedrooms_min: Optional[int] = None
    bedrooms_max: Optional[int] = None
    bathrooms_min: Optional[float] = None
    bathrooms_max: Optional[float] = None
    # User preference; False does not claim the property's pool field is false.
    pool: Optional[bool] = None

    def to_dict(self) -> dict:
        return asdict(self)


_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_UNIT = r"(?:k|m|thousand|million|dollars?)\b"
_PRICE = (
    rf"(?P<currency>\$|USD\s*)?\s*(?P<amount>{_NUMBER})\s*"
    rf"(?P<unit>{_UNIT})?\s*(?P<currency_word>USD|dollars?)?"
)
_PRICE_SECOND = (
    rf"(?P<currency2>\$|USD\s*)?\s*(?P<amount2>{_NUMBER})\s*"
    rf"(?P<unit2>{_UNIT})?\s*(?P<currency_word2>USD|dollars?)?"
)
_BEDROOM_TERM = r"(?:bedrooms?|beds?)"
_BATHROOM_TERM = r"(?:bathrooms?|baths?)"
_POOL_TERM = r"(?:(?:private|swimming)\s+)?pools?"


def load_valid_cities(path: Union[str, Path]) -> list[str]:
    """Load city names from a newline-delimited text file."""
    with Path(path).open(encoding="utf-8") as city_file:
        return [city.strip() for city in city_file if city.strip()]


def _price_to_int(amount: str, unit: Optional[str]) -> int:
    multiplier = {
        "k": 1_000,
        "thousand": 1_000,
        "m": 1_000_000,
        "million": 1_000_000,
    }.get((unit or "").lower(), 1)
    return int(float(amount.replace(",", "")) * multiplier)


def _find_price(
    match: Optional[re.Match[str]],
    currency_group: str = "currency",
    amount_group: str = "amount",
    unit_group: str = "unit",
    currency_word_group: str = "currency_word",
) -> Optional[int]:
    if match is None:
        return None
    if not any(
        match.group(group)
        for group in (currency_group, unit_group, currency_word_group)
    ):
        return None
    return _price_to_int(match.group(amount_group), match.group(unit_group))


def _extract_bedroom_filters(text: str, filters: PropertyFilters) -> None:
    range_match = re.search(
        rf"\bbetween\s+(?P<minimum>\d+)\s+and\s+(?P<maximum>\d+)\s+{_BEDROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if range_match:
        filters.bedrooms_min = int(range_match.group("minimum"))
        filters.bedrooms_max = int(range_match.group("maximum"))
        return

    minimum_match = re.search(
        rf"\b(?:at\s+least|minimum(?:\s+of)?)\s+(?P<count>\d+)\s+{_BEDROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if minimum_match:
        filters.bedrooms_min = int(minimum_match.group("count"))
        return

    maximum_match = re.search(
        rf"\b(?:up\s+to|no\s+more\s+than)\s+(?P<count>\d+)\s+{_BEDROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if maximum_match:
        filters.bedrooms_max = int(maximum_match.group("count"))
        return

    exact_match = re.search(
        rf"\b(?P<count>\d+)(?P<plus>\s*\+)?\s+{_BEDROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if exact_match:
        filters.bedrooms_min = int(exact_match.group("count"))
        if exact_match.group("plus") is None:
            filters.bedrooms_max = filters.bedrooms_min


def _extract_bathroom_filters(text: str, filters: PropertyFilters) -> None:
    range_match = re.search(
        rf"\bbetween\s+(?P<minimum>\d+(?:\.\d+)?)\s+and\s+"
        rf"(?P<maximum>\d+(?:\.\d+)?)\s+{_BATHROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if range_match:
        filters.bathrooms_min = float(range_match.group("minimum"))
        filters.bathrooms_max = float(range_match.group("maximum"))
        return

    minimum_match = re.search(
        rf"\b(?:at\s+least|minimum(?:\s+of)?)\s+"
        rf"(?P<count>\d+(?:\.\d+)?)\s+{_BATHROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if minimum_match:
        filters.bathrooms_min = float(minimum_match.group("count"))
        return

    maximum_match = re.search(
        rf"\b(?:up\s+to|no\s+more\s+than)\s+"
        rf"(?P<count>\d+(?:\.\d+)?)\s+{_BATHROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if maximum_match:
        filters.bathrooms_max = float(maximum_match.group("count"))
        return

    exact_match = re.search(
        rf"\b(?P<count>\d+(?:\.\d+)?)(?P<plus>\s*\+)?\s+"
        rf"{_BATHROOM_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if exact_match:
        filters.bathrooms_min = float(exact_match.group("count"))
        if exact_match.group("plus") is None:
            filters.bathrooms_max = filters.bathrooms_min


def _extract_pool_preference(text: str) -> Optional[bool]:
    negative_match = re.search(
        rf"\bwithout\s+(?:a\s+)?{_POOL_TERM}\b"
        rf"|\bno\s+{_POOL_TERM}\b"
        rf"|\b(?:do\s+not|don['’]t)\s+want\s+(?:a\s+)?{_POOL_TERM}\b",
        text,
        re.IGNORECASE,
    )
    if negative_match:
        return False

    positive_match = re.search(
        rf"\b(?:with|has)\s+(?:a\s+)?{_POOL_TERM}\b"
        rf"|,\s*a\s+{_POOL_TERM}\b"
        rf"|\band\s+a\s+{_POOL_TERM}\b"
        rf"|\bpool\s+required\b",
        text,
        re.IGNORECASE,
    )
    if positive_match:
        return True
    return None


class QueryParser:
    def __init__(self, valid_cities: Optional[Iterable[str]] = None) -> None:
        """Use distinct, non-empty ``L_City`` values supplied by the caller."""
        self._city_patterns: list[tuple[str, Pattern[str]]] = []
        seen_cities = set()
        for city in valid_cities if valid_cities is not None else ():
            canonical_city = city.strip()
            normalized_city = canonical_city.casefold()
            if not canonical_city or normalized_city in seen_cities:
                continue
            seen_cities.add(normalized_city)
            city_pattern = r"\s+".join(
                re.escape(part) for part in canonical_city.split()
            )
            self._city_patterns.append(
                (
                    canonical_city,
                    re.compile(
                        rf"(?<!\w){city_pattern}(?!\w)",
                        re.IGNORECASE,
                    ),
                )
            )
        self._city_patterns.sort(key=lambda item: len(item[0]), reverse=True)

    def _find_city(self, text: str) -> Optional[str]:
        matches = []
        for canonical_city, pattern in self._city_patterns:
            match = pattern.search(text)
            if match:
                matches.append((match.start(), -len(match.group()), canonical_city))
        if not matches:
            return None
        return min(matches)[2]

    def parse(self, text: str) -> PropertyFilters:
        filters = PropertyFilters()
        filters.city = self._find_city(text)
        range_match = re.search(
            rf"\bbetween\s+{_PRICE}\s+and\s+{_PRICE_SECOND}",
            text,
            re.IGNORECASE,
        )
        if range_match:
            filters.price_min = _find_price(range_match)
            filters.price_max = _find_price(
                range_match,
                "currency2",
                "amount2",
                "unit2",
                "currency_word2",
            )
        if filters.price_min is None and filters.price_max is None:
            max_match = re.search(
                rf"\b(?:under|below|less\s+than)\s+{_PRICE}",
                text,
                re.IGNORECASE,
            )
            min_match = re.search(
                rf"\b(?:over|above)\s+{_PRICE}", text, re.IGNORECASE
            )
            filters.price_max = _find_price(max_match)
            filters.price_min = _find_price(min_match)

        _extract_bedroom_filters(text, filters)
        _extract_bathroom_filters(text, filters)
        filters.pool = _extract_pool_preference(text)
        return filters
