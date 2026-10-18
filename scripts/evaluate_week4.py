"""Evaluate the Week 4 query parser against its manually labeled dataset."""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.query_parser import PropertyFilters, QueryParser, load_valid_cities


EVALUATION_PATH = PROJECT_ROOT / "data" / "week4" / "query_eval.json"
CITY_PATH = PROJECT_ROOT / "data" / "processed" / "valid_cities.txt"
CATEGORY_FIELDS = {
    "city": ("city",),
    "price": ("price_min", "price_max"),
    "bedrooms": ("bedrooms_min", "bedrooms_max"),
    "bathrooms": ("bathrooms_min", "bathrooms_max"),
    "pool": ("pool",),
}


def _load_records(path: Path) -> List[dict]:
    with path.open(encoding="utf-8") as evaluation_file:
        dataset = json.load(evaluation_file)
    records = dataset["records"]
    if len(records) != 50:
        raise ValueError(f"Expected 50 evaluation queries, found {len(records)}")
    return records


def _format_filters(filters: PropertyFilters) -> str:
    values = filters.to_dict()
    populated = []
    for field_name, value in values.items():
        if value is not None:
            formatted_value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, bool):
                formatted_value = str(value)
            populated.append(f"{field_name}={formatted_value}")
    return "{" + ", ".join(populated) + "}"


def evaluate(records: List[dict], parser: QueryParser) -> Tuple[int, Dict[str, int]]:
    correct_queries = 0
    category_correct = {category: 0 for category in CATEGORY_FIELDS}
    mismatches = []

    for record in records:
        expected = record.get("expected", {})
        predicted = parser.parse(record["query"])
        predicted_values = predicted.to_dict()
        query_matches = True
        mismatched_categories = []

        for category, fields in CATEGORY_FIELDS.items():
            matches = all(
                expected.get(field_name) == predicted_values[field_name]
                for field_name in fields
            )
            if matches:
                category_correct[category] += 1
            else:
                query_matches = False
                mismatched_categories.append(category)

        if query_matches:
            correct_queries += 1
        else:
            expected_filters = PropertyFilters(
                **{
                    field_name: expected.get(field_name)
                    for field_name in PropertyFilters.__dataclass_fields__
                }
            )
            mismatches.append(
                (record, expected_filters, predicted, mismatched_categories)
            )

    total = len(records)
    print(
        f"Overall exact-match accuracy: {correct_queries}/{total} "
        f"({correct_queries / total:.1%})"
    )
    print("Field-level accuracy:")
    for category, correct in category_correct.items():
        print(f"  {category}: {correct}/{total} ({correct / total:.1%})")

    print(f"Mismatched queries ({len(mismatches)}):")
    for record, expected_filters, predicted, categories in mismatches:
        print(f"  {record['id']} [{', '.join(categories)}]: {record['query']}")
        print(f"    expected:  {_format_filters(expected_filters)}")
        print(f"    predicted: {_format_filters(predicted)}")

    return correct_queries, category_correct


def main() -> None:
    records = _load_records(EVALUATION_PATH)
    valid_cities = load_valid_cities(CITY_PATH)
    parser = QueryParser(valid_cities=valid_cities)
    evaluate(records, parser)


if __name__ == "__main__":
    main()
