"""Evaluate only explicitly verified teammate-provided Week 3 annotations.

The input annotations are read-only. Teammate label names are mapped in memory
to the local five-label schema; their text and offsets are never rewritten.
"""

import json
import re
from collections import Counter
from pathlib import Path

from scripts.annotation_helper import generate_candidates
from scripts.interactive_annotator import LABELS, regex_version, test_manifest_path


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "labeled"
INPUT_PATH = DATA_DIR / "week3_teammate_gold_test_21.jsonl"
OUTPUT_PATH = DATA_DIR / "week3_teammate_gold_test_21_evaluation.json"
EXPECTED_RECORDS = 21
LABEL_MAP = {
    "BEDROOMS": "BEDROOM",
    "BATHROOMS": "BATHROOM",
    "BEDROOM": "BEDROOM",
    "BATHROOM": "BATHROOM",
    "SQFT": "SQFT",
    "PRICE": "PRICE",
    "AMENITY": "AMENITY",
}


def read_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_record(record, record_number):
    """Return concerns without rewriting or silently dropping annotations."""
    issues = []
    text = record.get("text")
    entities = record.get("entities")
    if not isinstance(text, str):
        return [{"record_number": record_number, "kind": "invalid_text", "detail": "text must be a string"}]
    if not isinstance(entities, list):
        return [{"record_number": record_number, "kind": "invalid_entities", "detail": "entities must be a list"}]

    valid_spans = []
    for entity_number, entity in enumerate(entities, 1):
        base = {"record_number": record_number, "entity_number": entity_number}
        if not isinstance(entity, dict):
            issues.append({**base, "kind": "invalid_structure", "detail": "entity must be an object"})
            continue
        start, end, source_label = entity.get("start"), entity.get("end"), entity.get("label")
        if (not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)):
            issues.append({**base, "kind": "invalid_offsets", "detail": "start/end must be integers"})
            continue
        if start < 0 or end <= start or end > len(text):
            issues.append({
                **base, "kind": "out_of_bounds", "start": start, "end": end,
                "text_length": len(text),
            })
            continue
        if not isinstance(source_label, str) or source_label not in LABEL_MAP:
            issues.append({**base, "kind": "unknown_label", "label": source_label})
            continue

        label = LABEL_MAP[source_label]
        surface = text[start:end]
        valid_spans.append((start, end, label, entity_number))
        if label not in LABELS:
            issues.append({**base, "kind": "mapped_label_outside_schema", "label": label})
        if (start > 0 and text[start - 1].isalnum()) or (
            end < len(text) and text[end].isalnum()
        ):
            issues.append({
                **base, "kind": "suspicious_token_boundary", "start": start,
                "end": end, "label": source_label, "surface": surface,
            })
        surface_folded = surface.casefold()
        expected_surface = {
            "BEDROOM": bool(re.search(r"\b(?:bedrooms?|beds?)\b|\d\s*(?:br|bd)\b", surface_folded)),
            "BATHROOM": bool(re.search(r"\b(?:bathrooms?|baths?)\b|\d(?:\.\d+)?\s*ba\b", surface_folded)),
            "SQFT": bool(re.search(r"\b(?:square\s+feet|sq\.?\s*ft\.?|sqft)\b", surface_folded)),
            "PRICE": bool(re.search(r"\d", surface_folded)),
            "AMENITY": bool(surface.strip()),
        }[label]
        if not expected_surface:
            issues.append({
                **base, "kind": "suspicious_label_surface_consistency",
                "label": source_label, "surface": surface,
            })

    for index, left in enumerate(valid_spans):
        for right in valid_spans[index + 1:]:
            if max(left[0], right[0]) < min(left[1], right[1]):
                issues.append({
                    "record_number": record_number,
                    "kind": "overlapping_entities",
                    "entity_numbers": [left[3], right[3]],
                    "spans": [[left[0], left[1], left[2]], [right[0], right[1], right[2]]],
                    "surfaces": [text[left[0]:left[1]], text[right[0]:right[1]]],
                })
    return issues


def entity_spans(record):
    """Map labels only; keep supplied offsets exactly as recorded."""
    return {
        (entity["start"], entity["end"], LABEL_MAP[entity["label"]])
        for entity in record["entities"]
    }


def score_counts(tp, predicted, gold):
    precision = tp / predicted if predicted else 0.0
    recall = tp / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "true_positives": tp,
        "false_positives": predicted - tp,
        "false_negatives": gold - tp,
        "predicted_entities": predicted,
        "gold_entities": gold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def diagnose_errors(text, predicted, gold):
    """Pair overlapping misses for boundary/label diagnostics; strict scores remain exact."""
    unmatched_pred = set(predicted - gold)
    unmatched_gold = set(gold - predicted)
    candidates = []
    for pred in unmatched_pred:
        for ref in unmatched_gold:
            overlap = max(0, min(pred[1], ref[1]) - max(pred[0], ref[0]))
            if overlap:
                priority = 0 if pred[:2] == ref[:2] and pred[2] != ref[2] else 1
                distance = abs(pred[0] - ref[0]) + abs(pred[1] - ref[1])
                candidates.append((priority, -overlap, distance, pred, ref))
    paired_pred, paired_gold, pairs = set(), set(), []
    for _, _, _, pred, ref in sorted(candidates):
        if pred in paired_pred or ref in paired_gold:
            continue
        kind = "label_disagreement" if pred[:2] == ref[:2] else "boundary_disagreement"
        pairs.append({
            "kind": kind,
            "predicted": {"start": pred[0], "end": pred[1], "label": pred[2], "surface": text[pred[0]:pred[1]]},
            "gold": {"start": ref[0], "end": ref[1], "label": ref[2], "surface": text[ref[0]:ref[1]]},
        })
        paired_pred.add(pred)
        paired_gold.add(ref)
    return {
        "boundary_or_label_disagreements": pairs,
        "false_positives_without_overlap": [
            {"start": s, "end": e, "label": label, "surface": text[s:e]}
            for s, e, label in sorted(unmatched_pred - paired_pred)
        ],
        "missed_spans_without_overlap": [
            {"start": s, "end": e, "label": label, "surface": text[s:e]}
            for s, e, label in sorted(unmatched_gold - paired_gold)
        ],
    }


def evaluate(records):
    if len(records) != len({record.get("id") for record in records}):
        duplicate_ids = [key for key, count in Counter(r.get("id") for r in records).items() if count > 1]
    else:
        duplicate_ids = []
    validation_issues = []
    for number, record in enumerate(records, 1):
        validation_issues.extend(validate_record(record, number))

    verified = [(number, record) for number, record in enumerate(records, 1)
                if record.get("verified") is True]
    unscorable = []
    scored_records = []
    for number, record in verified:
        record_issues = [issue for issue in validation_issues if issue["record_number"] == number]
        # Out-of-bounds/structurally invalid data cannot be compared safely.
        fatal = {"invalid_text", "invalid_entities", "invalid_structure", "invalid_offsets",
                 "out_of_bounds", "unknown_label", "mapped_label_outside_schema"}
        if any(issue["kind"] in fatal for issue in record_issues):
            unscorable.append({"record_number": number, "id": record.get("id"), "reason": "fatal span validation issue"})
            continue
        predicted = {tuple(span) for span in generate_candidates(record["text"])}
        gold = entity_spans(record)
        scored_records.append((number, record, predicted, gold))

    labels = sorted(LABELS)
    totals = {"tp": 0, "pred": 0, "gold": 0}
    by_label = {label: {"tp": 0, "pred": 0, "gold": 0} for label in labels}
    analyses = []
    for number, record, predicted, gold in scored_records:
        matches = predicted & gold
        totals["tp"] += len(matches)
        totals["pred"] += len(predicted)
        totals["gold"] += len(gold)
        for label in labels:
            by_label[label]["tp"] += sum(span[2] == label for span in matches)
            by_label[label]["pred"] += sum(span[2] == label for span in predicted)
            by_label[label]["gold"] += sum(span[2] == label for span in gold)
        diagnostics = diagnose_errors(record["text"], predicted, gold)
        analyses.append({
            "record_number": number, "id": record.get("id"),
            "exact_matches": len(matches),
            "false_positives": diagnostics["false_positives_without_overlap"]
                + [pair["predicted"] for pair in diagnostics["boundary_or_label_disagreements"]],
            "missed_gold": diagnostics["missed_spans_without_overlap"]
                + [pair["gold"] for pair in diagnostics["boundary_or_label_disagreements"]],
            **diagnostics,
        })

    result = {
        "dataset_provenance": "teammate-provided gold annotations; verified status is taken only from the source file",
        "input_file": INPUT_PATH.name,
        "expected_verified_records_as_requested": EXPECTED_RECORDS,
        "records_in_file": len(records),
        "verified_records_in_file": sum(record.get("verified") is True for record in records),
        "unverified_records_excluded": sum(record.get("verified") is not True for record in records),
        "scored_verified_records": len(scored_records),
        "unscorable_verified_records": unscorable,
        "status": "complete" if len(scored_records) == EXPECTED_RECORDS else "incomplete_source_verification_count_mismatch",
        "duplicate_record_ids": duplicate_ids,
        "label_mapping": LABEL_MAP,
        "extractor_regex_version": regex_version(),
        "scoring": "exact start/end offsets and mapped label; micro precision, recall, and F1",
        "overall": score_counts(totals["tp"], totals["pred"], totals["gold"]),
        "by_entity_type": {
            label: score_counts(counts["tp"], counts["pred"], counts["gold"])
            for label, counts in by_label.items()
        },
        "validation_issue_counts": dict(Counter(issue["kind"] for issue in validation_issues)),
        "validation_issues": validation_issues,
        "error_analysis": analyses,
        "note": "Suspicious but structurally valid spans are retained unchanged for scoring and listed separately in validation_issues.",
    }
    return result


def main():
    if not INPUT_PATH.is_file():
        raise SystemExit(f"Required teammate gold file is missing: {INPUT_PATH}")
    records = read_jsonl(INPUT_PATH)
    if len(records) != EXPECTED_RECORDS:
        raise SystemExit(
            f"Expected exactly {EXPECTED_RECORDS} records in {INPUT_PATH.name}; found {len(records)}"
        )
    verified_count = sum(record.get("verified") is True for record in records)
    if verified_count != EXPECTED_RECORDS:
        raise SystemExit(
            f"Expected all {EXPECTED_RECORDS} records to have verified: true; found {verified_count}"
        )
    results = evaluate(records)
    manifest = json.loads(test_manifest_path().read_text(encoding="utf-8"))
    results["matches_existing_frozen_extractor_manifest"] = (
        results["extractor_regex_version"] == manifest.get("regex_version")
    )
    if not results["matches_existing_frozen_extractor_manifest"]:
        raise SystemExit("Current extractor fingerprint does not match the frozen Week 3 manifest")
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
