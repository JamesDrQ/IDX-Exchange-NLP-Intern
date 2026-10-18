"""Compare original and current extractors on the Week 3 development split.

This evaluation uses AI-reviewed annotations and is provisional. It never reads
the test annotation file and does not treat AI-reviewed spans as human truth.
"""

import json
from collections import Counter
from pathlib import Path

from scripts.annotation_helper import generate_candidates


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "labeled"


def load_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_selected_jsonl(path, selected_indices):
    """Parse only requested source rows, leaving other split labels untouched."""
    selected_indices = set(selected_indices)
    records = {}
    with path.open(encoding="utf-8") as f:
        for index, line in enumerate(f):
            if index in selected_indices and line.strip():
                records[index] = json.loads(line)
    return records


def adjudicated_entities(record):
    """Apply clear text-supported rulings without editing the annotation file."""
    index = record["source_index"]
    text = record["text"]
    # Prior annotation-script substring matching created a few spans inside a
    # larger word (for example, "spa" inside "space"). These are not valid
    # exact-token entities under the requested span-boundary rule.
    entities = {
        tuple(entity) for entity in record["entities"]
        if not (
            (entity[0] > 0 and text[entity[0] - 1].isalnum())
            or (entity[1] < len(text) and text[entity[1]].isalnum())
        )
        and text[entity[0]:entity[1]].casefold() not in {
            "floor plan", "open floor plan", "living space", "outdoor space", "outdoor living"
        }
    }

    # The original four-bedroom configuration is historical; one bedroom was
    # converted to a bonus room. Do not score it as a current bedroom count.
    if index == 126:
        entities = {
            entity for entity in entities
            if not (
                entity[2] == "BEDROOM"
                and text[entity[0]:entity[1]].casefold() == "four-bedroom"
            )
        }

    # This home is explicitly under construction. Its design amenities are not
    # established as existing, so exclude that disputed class from scoring.
    if index == 209:
        entities = {entity for entity in entities if entity[2] != "AMENITY"}

    # The permitted bedroom/office addition's completion status is unresolved.
    if index == 243:
        entities = {
            entity for entity in entities
            if text[entity[0]:entity[1]].casefold() != "bedroom/office"
        }
    return entities


def filtered_predictions(index, text, entities):
    entities = {tuple(entity) for entity in entities}
    if index == 209:
        entities = {entity for entity in entities if entity[2] != "AMENITY"}
    if index == 243:
        entities = {
            entity for entity in entities
            if text[entity[0]:entity[1]].casefold() != "bedroom/office"
        }
    return entities


def diagnose(unmatched_predictions, unmatched_gold):
    """Separate overlapping label/boundary disagreements from FP/FN counts."""
    pairs = []
    for pred in unmatched_predictions:
        for gold in unmatched_gold:
            overlap = max(0, min(pred[1], gold[1]) - max(pred[0], gold[0]))
            if overlap:
                same_boundary = pred[:2] == gold[:2]
                same_label = pred[2] == gold[2]
                priority = 0 if same_boundary and not same_label else 1 if same_label else 2
                distance = abs(pred[0] - gold[0]) + abs(pred[1] - gold[1])
                pairs.append((priority, -overlap, distance, pred, gold))

    used_predictions, used_gold = set(), set()
    labels = boundaries = 0
    for _, _, _, pred, gold in sorted(pairs):
        if pred in used_predictions or gold in used_gold:
            continue
        if pred[:2] == gold[:2] and pred[2] != gold[2]:
            labels += 1
        else:
            boundaries += 1
        used_predictions.add(pred)
        used_gold.add(gold)

    false_positives = [x for x in unmatched_predictions if x not in used_predictions]
    missed = [x for x in unmatched_gold if x not in used_gold]
    return labels, boundaries, false_positives, missed


def evaluate(name, source_records, reviewed):
    tp = fp = fn = label_errors = boundary_errors = 0
    false_by_label, missed_by_label = Counter(), Counter()
    for index, reviewed_record in reviewed.items():
        source = source_records[index]
        text = source["text"]
        if name == "before":
            predicted = source["entities"]
        else:
            predicted = generate_candidates(text)
        pred = filtered_predictions(index, text, predicted)
        gold = adjudicated_entities(reviewed_record)
        tp += len(pred & gold)
        unmatched_predictions = pred - gold
        unmatched_gold = gold - pred
        labels, boundaries, false_positives, missed = diagnose(
            list(unmatched_predictions), list(unmatched_gold)
        )
        label_errors += labels
        boundary_errors += boundaries
        # Strict span evaluation counts a boundary/label mismatch as both one
        # unmatched prediction and one unmatched gold span.
        fp += len(unmatched_predictions)
        fn += len(unmatched_gold)
        false_by_label.update(entity[2] for entity in false_positives)
        missed_by_label.update(entity[2] for entity in missed)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "false_positives": fp,
        "missed_entities": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "overlapping_incorrect_labels": label_errors,
        "overlapping_boundary_errors": boundary_errors,
        "unmatched_false_positives_without_overlap": sum(false_by_label.values()),
        "missed_spans_without_overlap": sum(missed_by_label.values()),
        "false_positives_by_label": dict(false_by_label),
        "missed_entities_by_label": dict(missed_by_label),
    }


def run_evaluation():
    split = json.loads((DATA_DIR / "week3_split.json").read_text(encoding="utf-8"))
    development_indices = split["development"]
    original = load_selected_jsonl(
        DATA_DIR / "week3_auto_labels.jsonl", development_indices
    )
    reviewed_records = load_jsonl(DATA_DIR / "week3_ai_review_annotations.partial.jsonl")
    reviewed = {record["source_index"]: record for record in reviewed_records}
    if set(reviewed) != set(development_indices):
        raise ValueError("AI-reviewed records do not exactly cover the development split")

    # Index only the development rows for evaluation; test annotation records
    # are never loaded or consulted.
    sources = original
    invalid_reference_boundaries = sum(
        1
        for record in reviewed_records
        for start, end, _ in record["entities"]
        if (start > 0 and record["text"][start - 1].isalnum())
        or (end < len(record["text"]) and record["text"][end].isalnum())
    )
    return {
        "status": "provisional_ai_reviewed_reference",
        "split": "development",
        "records": len(development_indices),
        "discarded_ai_reference_spans_with_midword_boundaries": invalid_reference_boundaries,
        "excluded_ambiguous_items": [
            {"source_index": 209, "item": "AMENITY", "reason": "Under-construction features are not yet established as existing."},
            {"source_index": 243, "item": "bedroom/office", "reason": "Addition completion status is unresolved."},
            {"source_index": 126, "item": "four-bedroom", "reason": "Historical count predates conversion of one bedroom."},
        ],
        "before": evaluate("before", sources, reviewed),
        "after": evaluate("after", sources, reviewed),
    }


if __name__ == "__main__":
    print(json.dumps(run_evaluation(), indent=2))
