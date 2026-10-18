import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.annotation_helper import generate_candidates


DATA_DIR = Path("data/labeled")
LABELS = {"BEDROOM", "BATHROOM", "PRICE", "SQFT", "AMENITY"}


def data_path(split=None):
    if split == "development":
        return DATA_DIR / "week3_dev_annotations.jsonl"
    if split == "test":
        return DATA_DIR / "week3_test_annotations.jsonl"
    return DATA_DIR / "week3_annotations.jsonl"


def test_manifest_path():
    return DATA_DIR / "week3_test_evaluation_manifest.json"


def regex_version():
    """Fingerprint code and taxonomy that determine frozen predictions."""
    root = Path(__file__).resolve().parent.parent
    sources = (
        root / "scripts" / "entity_extractor.py",
        root / "scripts" / "annotation_helper.py",
        root / "data" / "processed" / "taxonomy.json",
    )
    digest = hashlib.sha256()
    for source in sources:
        digest.update(source.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def initialize_test_annotations():
    """Create a test review file once, preserving predictions as suggestions."""
    path = data_path("test")
    manifest_path = test_manifest_path()
    version = regex_version()

    if path.exists():
        if not manifest_path.exists():
            raise FileExistsError(
                f"{path} already exists without a freeze manifest; refusing to replace it."
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("regex_version") != version:
            raise RuntimeError(
                "The frozen extractor or taxonomy changed after test initialization."
            )
        split = json.loads((DATA_DIR / "week3_split.json").read_text(encoding="utf-8"))
        if manifest.get("test_source_indices") != split.get("test"):
            raise RuntimeError("Freeze manifest does not match the current test split")
        with path.open(encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        if len(records) != 30 or [r.get("source_index") for r in records] != split["test"]:
            raise ValueError("Existing test annotations do not match the 30-record split")
        for record in records:
            if record.get("regex_version") != version:
                raise RuntimeError("A test record has a different frozen regex version")
            validate_entities(record.get("predicted_entities"), record.get("text", ""))
            validate_entities(record.get("entities"), record.get("text", ""))
        return records

    split_path = DATA_DIR / "week3_split.json"
    source_path = DATA_DIR / "week3_auto_labels.jsonl"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    indices = split["test"]
    if len(indices) != 30 or len(set(indices)) != 30:
        raise ValueError("Expected exactly 30 unique test split indices")
    with source_path.open(encoding="utf-8") as f:
        source_rows = [json.loads(line) for line in f]
    if len(source_rows) != 250 or max(indices, default=-1) >= len(source_rows):
        raise ValueError("Automatic source data does not contain the expected 250 listings")

    records = []
    for index in indices:
        source = source_rows[index]
        text = source["text"]
        predictions = generate_candidates(text)
        validate_entities(predictions, text)
        records.append({
            "source_index": index,
            "listing_id": source["listing_id"],
            "text": text,
            # These are proposals from the frozen extractor, never labels
            # accepted as ground truth by initialization.
            "predicted_entities": predictions,
            "entities": [list(entity) for entity in predictions],
            "human_verified": False,
            "review_source": "regex_suggestions_pending_human_review",
            "regex_version": version,
        })

    manifest = {
        "regex_version": version,
        "source_files": [
            "scripts/entity_extractor.py",
            "scripts/annotation_helper.py",
            "data/processed/taxonomy.json",
        ],
        "test_source_indices": indices,
        "record_count": len(records),
        "predictions_are_suggestions_not_ground_truth": True,
    }

    # Exclusive creation prevents accidental replacement of any prior work.
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing_manifest != manifest:
            raise RuntimeError("Existing freeze manifest differs; refusing to initialize")
    else:
        with manifest_path.open("x", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.write("\n")
    with path.open("x", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records


def validate_entities(entities, text):
    """Raise ValueError if a span cannot safely be saved for this text."""
    if not isinstance(entities, list):
        raise ValueError("Entities must be a list")

    for entity in entities:
        if not isinstance(entity, (list, tuple)) or len(entity) != 3:
            raise ValueError(f"Invalid entity structure: {entity!r}")

        start, end, label = entity
        if (not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)):
            raise ValueError(f"Entity offsets must be integers: {entity!r}")
        if start < 0 or end <= start or end > len(text):
            raise ValueError(f"Entity offsets out of range: {entity!r}")
        if not isinstance(label, str) or label not in LABELS:
            raise ValueError(f"Invalid entity label: {label!r}")


def save_records(records, path):
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    temp_path.replace(path)


def _deduplicate(entities):
    result = []
    seen = set()
    for start, end, label in entities:
        item = (start, end, label)
        if item not in seen:
            result.append([start, end, label])
            seen.add(item)
    return result


def review_record(record, records, path, input_fn=input, output_fn=print):
    """Review one record. Return False when the reviewer asks to quit."""
    if record.get("human_verified") is True:
        return True

    text = record["text"]
    existing = [list(entity) for entity in record.get("entities", [])]
    suggestions = record.get("predicted_entities")
    if suggestions is None:
        suggestions = generate_candidates(text)
    validate_entities(existing, text)
    validate_entities(suggestions, text)
    combined = _deduplicate(existing + suggestions)

    output_fn("\n" + "=" * 70)
    output_fn(f"Listing ID: {record.get('listing_id', 'unknown')}")
    output_fn("\nFULL TEXT:\n" + text)
    output_fn("\nENTITY SPANS (current and suggested):")
    existing_set = {tuple(entity) for entity in existing}
    predicted_set = {
        tuple(entity) for entity in record.get("predicted_entities", [])
    }
    for number, (start, end, label) in enumerate(combined, 1):
        if (start, end, label) in predicted_set and record.get("human_verified") is not True:
            status = "suggested"
        else:
            status = "current" if (start, end, label) in existing_set else "suggested"
        output_fn(
            f"{number:2}. {status:9} {label:10} "
            f"[{start}, {end}] {text[start:end]}"
        )

    answer = input_fn(
        "\nEnter entity numbers to REMOVE, 'e' to edit a span/label, "
        "'a' to keep all suggestions, Enter to keep current entities only, "
        "or 'q' to quit: "
    ).strip().lower()
    if answer == "q":
        output_fn("Progress saved. Exiting.")
        return False

    if answer == "a":
        approved = combined
    elif answer == "e":
        approved = [list(entity) for entity in combined]
        while True:
            selection = input_fn(
                "Entity number to edit (Enter when done): "
            ).strip()
            if not selection:
                break
            if selection.lower() == "q":
                approved.sort(key=lambda entity: (entity[0], entity[1], entity[2]))
                record["entities"] = _deduplicate(approved)
                record["human_verified"] = False
                validate_entities(record["entities"], text)
                save_records(records, path)
                output_fn("Progress saved as unverified. Exiting.")
                return False
            try:
                number = int(selection)
                if number < 1 or number > len(approved):
                    raise ValueError("Entity number is out of range")
                specification = input_fn(
                    "Replacement as START:END,LABEL or exact text,LABEL: "
                ).strip()
                replacement = _parse_entity_specification(
                    specification, text, anchor=approved[number - 1][0]
                )
                approved[number - 1] = replacement
                validate_entities(approved, text)
                output_fn(
                    f"Edited: {replacement[2]} [{replacement[0]}, {replacement[1]}] "
                    f"{text[replacement[0]:replacement[1]]}"
                )
            except (ValueError, IndexError) as error:
                output_fn(f"Invalid edit: {error}")
    elif not answer:
        approved = existing
    else:
        try:
            removed = {int(value.strip()) for value in answer.split(",")}
        except ValueError:
            output_fn("Invalid selection; record not changed.")
            return True
        if any(number < 1 or number > len(combined) for number in removed):
            output_fn("Invalid selection; record not changed.")
            return True
        approved = [
            entity for number, entity in enumerate(combined, 1)
            if number not in removed
        ]

    approved = [list(entity) for entity in approved]
    while True:
        extra = input_fn(
            "Add missing entity as text,LABEL (Enter when done, 'q' to save and quit): "
        ).strip()
        if not extra:
            break
        if extra.lower() == "q":
            record["entities"] = _deduplicate(approved)
            validate_entities(record["entities"], text)
            record["human_verified"] = False
            save_records(records, path)
            output_fn("Progress saved as unverified. Exiting.")
            return False

        try:
            matches = _parse_entity_specification(extra, text, all_occurrences=True)
            if not matches:
                raise ValueError("Text not found in listing")

            approved = _deduplicate(approved + matches)
            validate_entities(approved, text)
            for start, end, entity_label in matches:
                output_fn(
                    f"Added: {entity_label} [{start}, {end}] {text[start:end]}"
                )
        except ValueError as error:
            output_fn(f"Invalid entity: {error}")

    approved.sort(key=lambda entity: (entity[0], entity[1], entity[2]))
    validate_entities(approved, text)
    record["entities"] = approved
    # Save edits as resumable progress before asking whether review is complete.
    record["human_verified"] = False
    save_records(records, path)

    confirmation = input_fn(
        "Type YES only if you reviewed the complete listing, including possible "
        "missed entities: "
    ).strip()
    if confirmation == "YES":
        record["human_verified"] = True
        save_records(records, path)

    return True


def _parse_entity_specification(specification, text, anchor=None, all_occurrences=False):
    """Parse an exact-offset edit or text,label addition."""
    value, label = specification.rsplit(",", 1)
    label = label.strip().upper()
    if label not in LABELS:
        raise ValueError(f"Unknown entity label: {label}")
    value = value.strip()
    offset_match = re.fullmatch(r"(\d+):(\d+)", value)
    if offset_match:
        entity = [int(offset_match.group(1)), int(offset_match.group(2)), label]
        validate_entities([entity], text)
        return [entity] if all_occurrences else entity

    matches = [
        [match.start(), match.end(), label]
        for match in re.finditer(re.escape(value), text, re.IGNORECASE)
    ]
    if not matches:
        raise ValueError("Text not found in listing")
    if all_occurrences:
        return matches
    if anchor is not None:
        return min(matches, key=lambda entity: abs(entity[0] - anchor))
    if len(matches) > 1:
        raise ValueError("Text occurs multiple times; use START:END,LABEL")
    return matches[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review Week 3 entity annotations")
    parser.add_argument(
        "--split", choices=("development", "test"),
        help="Review the isolated development or held-out test annotation file",
    )
    args = parser.parse_args(argv)
    if args.split == "test":
        records = initialize_test_annotations()
        path = data_path("test")
    else:
        path = data_path(args.split)
        with path.open(encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]

    total = len(records)
    for index, record in enumerate(records):
        if record.get("human_verified") is True:
            continue
        print(f"\nListing {index + 1}/{total}")
        if not review_record(record, records, path):
            break
        completed = sum(r.get("human_verified") is True for r in records)
        print(f"Saved progress: {completed}/{total} human-verified")

    completed = sum(r.get("human_verified") is True for r in records)
    print(f"\nAnnotation session finished. Verified: {completed}/{total}")


if __name__ == "__main__":
    main()
