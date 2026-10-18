"""Strict held-out Week 3 entity evaluation.

This script refuses to score until all 30 test listings have explicit human
verification and the stored extractor fingerprint still matches the frozen
version used to create their predictions.
"""

import json
from pathlib import Path

from scripts.annotation_helper import generate_candidates
from scripts.interactive_annotator import (
    LABELS,
    regex_version,
    test_manifest_path,
    validate_entities,
)


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "labeled"
ANNOTATION_PATH = DATA_DIR / "week3_test_annotations.jsonl"
SPLIT_PATH = DATA_DIR / "week3_split.json"


def _read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _validate_unique_spans(entities, text, context):
    validate_entities(entities, text)
    spans = [tuple(entity) for entity in entities]
    if len(spans) != len(set(spans)):
        raise ValueError(f"Duplicate entity spans in {context}")
    if any(label not in LABELS for _, _, label in spans):
        raise ValueError(f"Unexpected entity label in {context}")


def evaluate_test_records(records, expected_indices, manifest, current_version):
    """Validate the complete test set before returning strict micro metrics."""
    if len(expected_indices) != 30 or len(records) != 30:
        raise ValueError("Test evaluation requires exactly 30 split records")

    indices = [record.get("source_index") for record in records]
    if len(indices) != len(set(indices)) or set(indices) != set(expected_indices):
        raise ValueError("Test annotations must cover the 30 split indices exactly once")

    unverified = [
        record.get("listing_id", record.get("source_index"))
        for record in records
        if record.get("human_verified") is not True
    ]
    if unverified:
        raise RuntimeError(
            f"Evaluation blocked: {len(unverified)}/30 test records are not human-verified."
        )

    if manifest.get("record_count") != 30 or manifest.get("test_source_indices") != list(expected_indices):
        raise ValueError("Freeze manifest does not match the test split")
    if manifest.get("predictions_are_suggestions_not_ground_truth") is not True:
        raise ValueError("Freeze manifest lacks suggestion provenance")
    frozen_version = manifest.get("regex_version")
    if not frozen_version or frozen_version != current_version:
        raise RuntimeError(
            "Evaluation blocked: current extractor/taxonomy does not match the frozen test version."
        )

    total_tp = total_pred = total_gold = 0
    for record in records:
        if record.get("regex_version") != frozen_version:
            raise ValueError(
                f"Record {record.get('source_index')} has a different extractor version"
            )
        text = record.get("text")
        if not isinstance(text, str):
            raise ValueError(f"Missing text for record {record.get('source_index')}")
        predicted = record.get("predicted_entities")
        gold = record.get("entities")
        _validate_unique_spans(predicted, text, "frozen predictions")
        _validate_unique_spans(gold, text, "human annotations")

        current_predictions = generate_candidates(text)
        if [list(entity) for entity in predicted] != current_predictions:
            raise RuntimeError(
                f"Frozen prediction mismatch for source index {record['source_index']}"
            )

        predicted_set = {tuple(entity) for entity in predicted}
        gold_set = {tuple(entity) for entity in gold}
        total_tp += len(predicted_set & gold_set)
        total_pred += len(predicted_set)
        total_gold += len(gold_set)

    precision = total_tp / total_pred if total_pred else 0.0
    recall = total_tp / total_gold if total_gold else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "evaluation": "held_out_test_strict_entity_level",
        "records": len(records),
        "human_verified_records": len(records),
        "regex_version": frozen_version,
        "true_positives": total_tp,
        "predicted_entities": total_pred,
        "human_entities": total_gold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def run_evaluation():
    split = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    expected_indices = split["test"]
    records = _read_jsonl(ANNOTATION_PATH)
    manifest = json.loads(test_manifest_path().read_text(encoding="utf-8"))
    return evaluate_test_records(
        records,
        expected_indices,
        manifest,
        regex_version(),
    )


def main():
    try:
        results = run_evaluation()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
