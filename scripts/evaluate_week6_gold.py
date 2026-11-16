"""Evaluate ONLY human-verified Week 6 labels in an annotation CSV.

Usage from project root:
    python -m scripts.evaluate_week6_gold

Gold convention:
- Numeric/city fields: exact gold value; 'unknown' for unverified/missing.
- Flags: true / false / unknown (unknown excluded from accuracy).
- Keyword/amenity sets: JSON array, e.g. ["needs_repairs"] or [].
- Blank gold cell: not annotated and excluded, never treated as a negative.
- review_status: done (or verified/yes) to include that listing.
"""

import argparse
from collections import defaultdict
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

from scripts.prepare_week6_gold import ENTITIES, FLAGS, KEYWORDS
from scripts.signal_extractor import SignalExtractor

DONE = {"done", "verified", "yes"}
MISSING = {"unknown", "null", "none", "n/a"}


def bool_value(s, *, allow_unknown=True):
    s = str(s).strip().casefold()
    if s in {"true", "1", "yes"}:
        return True
    if s in {"false", "0", "no"}:
        return False
    if allow_unknown and s in MISSING:
        return None
    raise ValueError(f"invalid flag label: {s!r}; use true/false/unknown")


def entity_value(key, s):
    value = str(s).strip()
    if value.casefold() in MISSING:
        return None
    if key == "city":
        return " ".join(value.casefold().split())
    try:
        return Decimal(value)
    except InvalidOperation as e:
        raise ValueError(f"invalid numeric {key} value: {value!r}") from e


def tag_set(value):
    """Require JSON arrays; [] is an explicit negative gold label."""
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"expected JSON array of strings, e.g. [\"near_lake\"] or []: {value!r}") from e
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise ValueError(f"expected JSON array of strings, got {value!r}")
    return {x.casefold().strip() for x in parsed if x.strip()}


# These aliases are explicitly required by docs/week6_annotation_guidelines.md.
# Keep the table intentionally narrow: labels such as "private balcony" and
# "balcony", or "ocean view" and "ocean views", carry distinctions the guide
# says to preserve (or does not authorize collapsing).
_CANONICAL_ALIASES = {
    "condition": {
        "fresh paint": "freshly painted",
    },
    "location": {
        "just minutes": "minutes from",
        "just minutes from": "minutes from",
    },
    "property_type": {
        "townhouse": "townhome",
        "condominium": "condo",
        "single family residence": "single family home",
    },
    "amenities": {
        "walk in closets": "walk in closet",
        "walk in closet": "walk in closet",
        "walk in shower": "walk in shower",
        "walk in pantry": "walk in pantry",
    },
}
_HYPHENS = "-\u2010\u2011\u2012\u2013\u2014\u2015"


def canonical_tag(category, value):
    """Apply only the category aliases and hyphen rules in the annotation guide."""
    label = str(value).casefold().strip()
    label = "".join(" " if char in _HYPHENS else char for char in label)
    label = " ".join(label.split())
    return _CANONICAL_ALIASES.get(category, {}).get(label, label)


def normalized_tag_set(value, *, category, normalization="strict"):
    """Parse one tag array and normalize symmetrically for the chosen metric."""
    labels = tag_set(value)
    if normalization == "strict":
        return labels
    if normalization != "canonical":
        raise ValueError("normalization must be 'strict' or 'canonical'")
    return {canonical_tag(category, label) for label in labels}


def tag_counts(gold_set, pred_set):
    """Return label-instance TP/FP/FN counts for two sets."""
    return (
        len(gold_set & pred_set),
        len(pred_set - gold_set),
        len(gold_set - pred_set),
    )


def _metric_summary(counts):
    tp, fp, fn = counts
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def _print_text_metrics(title, tag_counts_by_category, row_counts, categories):
    print(f"\nFree-text {title} micro Precision / Recall / F1:")
    overall = [0, 0, 0]
    summaries = {}
    for category in categories:
        counts = tuple(tag_counts_by_category[category])
        summary = _metric_summary(counts)
        summaries[category] = summary
        print(
            f"  {category:16s} rows={row_counts[category]:3d}  "
            f"P={summary['precision']:.3f} R={summary['recall']:.3f} "
            f"F1={summary['f1']:.3f} TP={summary['tp']} FP={summary['fp']} FN={summary['fn']}"
        )
        overall = [a + b for a, b in zip(overall, counts)]
    summary = _metric_summary(tuple(overall))
    summaries["all"] = summary
    print(
        f"  {'ALL TEXT LABELS':16s} P={summary['precision']:.3f} "
        f"R={summary['recall']:.3f} F1={summary['f1']:.3f} "
        f"TP={summary['tp']} FP={summary['fp']} FN={summary['fn']}"
    )
    return summaries


def pct(n, d):
    return f"{100*n/d:.1f}%" if d else "n/a"


def evaluate(input_path, *, recompute_predictions=False, normalization="strict"):
    if normalization not in {"strict", "canonical", "both"}:
        raise ValueError("normalization must be 'strict', 'canonical', or 'both'")
    checked = 0
    total_rows = 0
    matched = defaultdict(int)
    annotated = defaultdict(int)
    counts_by_mode = {
        mode: defaultdict(lambda: [0, 0, 0]) for mode in ("strict", "canonical")
    }
    tag_rows = defaultdict(int)
    extractor = SignalExtractor() if recompute_predictions else None
    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            total_rows += 1
            if (row.get("review_status") or "").strip().casefold() not in DONE:
                continue
            checked += 1
            listing_id = row.get("listing_id", "<unknown>")
            try:
                signals = None
                if extractor is not None:
                    source_fields = json.loads(row.get("source_fields_json") or "{}")
                    if not isinstance(source_fields, dict):
                        raise ValueError("source_fields_json must contain a JSON object")
                    signals = extractor.extract_signals({
                        **source_fields,
                        "L_ListingID": listing_id,
                        "L_Remarks": row.get("remarks") or "",
                    })
                for key in ENTITIES:
                    gold = (row.get(f"gold_entity_{key}") or "").strip()
                    if not gold or gold.casefold() in MISSING:
                        continue
                    pred = (
                        signals["entities"].get(key) if signals is not None
                        else row.get(f"pred_entity_{key}", "unknown")
                    )
                    if pred is None:
                        pred = "unknown"
                    annotated[f"entity_{key}"] += 1
                    matched[f"entity_{key}"] += entity_value(key, gold) == entity_value(key, pred)
                for key in FLAGS:
                    gold = (row.get(f"gold_flag_{key}") or "").strip()
                    if not gold or gold.casefold() in MISSING:
                        continue
                    pred = (
                        signals["flags"].get(key) if signals is not None
                        else row.get(f"pred_flag_{key}", "unknown")
                    )
                    if isinstance(pred, bool):
                        pred = str(pred).lower()
                    elif pred is None:
                        pred = "unknown"
                    annotated[f"flag_{key}"] += 1
                    matched[f"flag_{key}"] += bool_value(gold, allow_unknown=False) == bool_value(pred)
                for key in [*KEYWORDS, "amenities"]:
                    prefix = f"keyword_{key}" if key != "amenities" else "amenities"
                    gold_text = (row.get(f"gold_{prefix}") or "").strip()
                    if not gold_text:
                        continue
                    if signals is None:
                        pred_text = row.get(f"pred_{prefix}") or "[]"
                    else:
                        values = signals["amenities"] if key == "amenities" else signals["keywords"][key]
                        pred_text = json.dumps(values, ensure_ascii=False)
                    tag_rows[key] += 1
                    for mode in ("strict", "canonical"):
                        gold_set = normalized_tag_set(gold_text, category=key, normalization=mode)
                        pred_set = normalized_tag_set(pred_text, category=key, normalization=mode)
                        counts = counts_by_mode[mode][key]
                        for index, count in enumerate(tag_counts(gold_set, pred_set)):
                            counts[index] += count
                    annotated[f"tag_{key}"] += 1
            except ValueError as e:
                raise ValueError(f"Listing {listing_id}: {e}") from e

    print(f"Reviewed: {checked}/{total_rows} listings (only review_status=done/verified/yes)")
    print("\nStructured field agreement (human gold, known gold values only):")
    n_entity = d_entity = n_flag = d_flag = 0
    for section, keys in (("entity", ENTITIES), ("flag", FLAGS)):
        for key in keys:
            metric = f"{section}_{key}"
            n, d = matched[metric], annotated[metric]
            print(f"  {metric:24s} {n:3d}/{d:<3d} {pct(n, d)}")
            if section == "entity":
                n_entity += n; d_entity += d
            else:
                n_flag += n; d_flag += d
    print(f"  {'ENTITY AGGREGATE':24s} {n_entity}/{d_entity} {pct(n_entity, d_entity)}")
    print(f"  {'FLAG AGGREGATE':24s} {n_flag}/{d_flag} {pct(n_flag, d_flag)}")
    total_agree, total_seen = n_entity+n_flag, d_entity+d_flag
    print(f"  {'STRUCTURED AGGREGATE':24s} {total_agree}/{total_seen} {pct(total_agree, total_seen)}")
    categories = [*KEYWORDS, "amenities"]
    summaries = {}
    modes_to_print = ("strict", "canonical") if normalization == "both" else (normalization,)
    for mode in modes_to_print:
        title = "exact-label (strict)" if mode == "strict" else "canonical-label"
        summaries[mode] = _print_text_metrics(title, counts_by_mode[mode], tag_rows, categories)
    resolved = {}
    if normalization == "both":
        print("\nLabel-instance mismatches reconciled by documented normalization:")
        for category in [*categories, "all"]:
            strict = summaries["strict"][category]
            canonical = summaries["canonical"][category]
            fp_resolved = strict["fp"] - canonical["fp"]
            fn_resolved = strict["fn"] - canonical["fn"]
            resolved[category] = {"fp": fp_resolved, "fn": fn_resolved}
            print(f"  {category:16s} FP={fp_resolved} FN={fn_resolved}")
    if not checked:
        print("\nNo reviewed rows yet: annotation CSV is only a template.")
    print("\nCaution: gold=unknown/blank is excluded; confirm rubric metric before asserting a target was met.")
    selected = "strict" if normalization in {"strict", "both"} else "canonical"
    summary = summaries[selected]["all"]
    return {
        "reviewed": checked,
        "structured_correct": total_agree,
        "structured_total": total_seen,
        "tags_tp": summary["tp"],
        "tags_fp": summary["fp"],
        "tags_fn": summary["fn"],
        "tags_f1": summary["f1"],
        "text_metrics": summaries,
        "normalization_resolved": resolved,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/processed/week6_gold_review.csv"))
    parser.add_argument(
        "--recompute-predictions", action="store_true",
        help="run the current SignalExtractor over Remarks/source fields in memory",
    )
    parser.add_argument(
        "--normalization", choices=("strict", "canonical", "both"), default="strict",
        help="text-label metric: strict preserves original exact matching; canonical applies documented aliases symmetrically",
    )
    args = parser.parse_args()
    if args.recompute_predictions:
        evaluate(args.input, recompute_predictions=True, normalization=args.normalization)
    else:
        evaluate(args.input, normalization=args.normalization)


if __name__ == "__main__":
    main()
