# Week 3 entity extraction: final status

## Scope and frozen implementation

Week 3's `EntityExtractor` is a rules-based span extractor for `BEDROOM`,
`BATHROOM`, `SQFT`, `PRICE`, and `AMENITY`. Its span API returns exact
`[start, end, label]` offsets. `scripts/annotation_helper.py` delegates to this
shared implementation.

The frozen implementation includes quantity patterns for numeric and spelled
bedroom/bathroom counts, fractions and common count descriptions; square-foot
forms; context-aware price patterns and exclusions; and amenity matching from
the Week 1 taxonomy. Amenity extraction prefers longer overlapping terms,
supports a limited modifier list, excludes selected generic phrases, and
filters clear nearby-public-feature contexts. A small supplemental term list
covers selected development examples. The extractor fingerprint for the
reported teammate evaluation matches the freeze manifest:

```text
7d8efbf7fbf14bcbd2bafd695755b31f6ce2ec2d11700bb99a2f0ddb93a1e7eb
```

No extractor rules or predictions were changed for the teammate evaluation,
five-record audit, or this final documentation. No additional annotation,
verification, or test-set tuning was performed.

## Dataset inventory and preparation

The files represent distinct data stages and references:

| Artifact | Records | What it represents |
| --- | ---: | --- |
| `data/labeled/week3_annotation_sample.csv` | 250 | Reproducible sample of source remarks, selected with seed 42 from the cleaned listing data. |
| `data/labeled/week3_annotations.jsonl` | 250 | Annotation scaffold for those remarks. |
| `data/labeled/week3_auto_labels.jsonl` | 250 | Extractor-generated proposals; every record has `human_verified: false`. These are automatically labeled remarks, not 250 human-verified annotations. |
| `data/labeled/week3_split.json` | 30 development, 30 local test, 190 remaining | Fixed-seed partition of the 250 records; source row 0 is kept in development. |
| `data/labeled/week3_dev_annotations.jsonl` | 30 | Development split records. The current file carries no human verification. |
| `data/labeled/week3_ai_review_annotations.partial.jsonl` | 30 | Separate AI-reviewed development reference used for provisional comparison; it is not human-verified truth. |
| `data/labeled/week3_test_annotations.jsonl` | 30 | Local held-out split annotations. Currently 10/30 carry `human_verified: true`; strict test evaluation is therefore blocked. |
| `data/labeled/week3_teammate_gold_test_21.jsonl` | 21 | Separate teammate-provided gold dataset; all 21 records carry `verified: true`. That flag denotes the teammate-provided source status and is not a claim that the user personally verified them. |

Preparation entry points are `scripts/prepare_week3_samples.py`,
`scripts/prepare_week3_annotations.py`, `scripts/generate_week3_labels.py`,
`scripts/split_week3_data.py`, and `scripts/prepare_week3_dev.py`. The review UI
is `scripts/interactive_annotator.py`. Several creation paths use exclusive
file creation and intentionally refuse to overwrite existing work.

## Evaluation scripts and scoring

- `python -m scripts.evaluate_week3_dev` compares the current extractor and
  original suggestions against the 30-record AI-reviewed development
  reference. It never reads the held-out annotation file. It applies its
  documented exclusions in memory only.
- `python -m scripts.evaluate_week3_teammate_gold` reads only
  `week3_teammate_gold_test_21.jsonl`, requires exactly 21 records with
  `verified: true`, maps `BEDROOMS` to `BEDROOM` and `BATHROOMS` to `BATHROOM`
  in memory, checks span validity and the frozen fingerprint, and writes the
  separate `week3_teammate_gold_test_21_evaluation.json` report.
- `python -m scripts.evaluate_week3_test` evaluates the local 30-record test
  split only after all records are human-verified and its freeze checks pass.
  It currently exits with `Evaluation blocked: 20/30 test records are not
  human-verified.`

Metrics use strict exact offset-and-label set matches. Thus, a span boundary
disagreement counts as one false positive and one false negative. Diagnostic
reports can pair overlapping mismatches to make those cases easier to inspect;
that pairing does not change the scoring method.

## Results

The two F1 values below use different datasets and different annotation
references. They must not be read as a before/after comparison or as scores on
one common test set.

| Split and reference | Precision | Recall | F1 | Exact counts |
| --- | ---: | ---: | ---: | --- |
| Development, 30 records; AI-reviewed annotations after documented in-memory exclusions | 86.7% | 60.3% | **71.1%** | 442 TP, 68 FP, 291 FN |
| Teammate-provided gold test, 21 records; labels mapped to local schema | 25.9% | 69.7% | **37.8%** | 85 TP, 243 FP, 37 FN |

The development comparison is provisional and optimistically biased: the
development examples informed phrase additions and were also used to measure
the updated extractor. Twelve AI-reviewed spans with mid-word boundaries and
several noted ambiguous items are excluded in the evaluator's derived view;
the source annotation file is not edited.

The 21-record teammate dataset is separate from the local 30-record held-out
split. A five-record audit using seed 42 found likely incomplete AMENITY
coverage, inconsistent span boundaries, and genuine regex errors. For
example, the extractor matched `spa` where surrounding language signaled a
style rather than an installed feature. The audit also found many plausible
taxonomy-supported property features absent from gold. Without a complete
annotation policy for whether ordinary rooms and broad feature descriptions
are exhaustive AMENITY labels, not every extractor-only span can be
definitively called a gold omission.

These reference limitations make the teammate score difficult to interpret
as pure extractor accuracy. They do not change the result: the **85% test F1
target has not been met**. The local 30-record test score remains unavailable
because 20 records are not verified. Week 3 is being documented as-is so work
can proceed to Week 4 without further manual annotation or tuning against test
examples.

## Development diagnostics

The development evaluator's original and updated results were:

| Extractor | Precision | Recall | F1 | TP / FP / FN |
| --- | ---: | ---: | ---: | --- |
| Original regex predictions | 72.5% | 42.8% | 53.9% | 314 / 119 / 419 |
| Updated regex and taxonomy matching | 86.7% | 60.3% | 71.1% | 442 / 68 / 291 |

Overlapping boundary disagreements decreased from 74 to 44; exact-boundary
label disagreements were zero in both comparisons. Remaining missed spans
were mostly AMENITY spans. These development figures are not an independent
estimate of performance because the split was used during extractor work.

## Tests

Run the available Week 3 test modules with:

```bash
python -m unittest tests.test_week3_annotation tests.test_week3_entity_extractor tests.test_week3_interactive_annotator tests.test_week3_test_workflow
```

All 25 Week 3 tests pass. `python -m unittest discover -s tests` also runs
those 25 successfully but reports import errors for `tests/test_setup.py`
(`mysql.connector` missing) and `tests/test_week2.py` (`pytest` missing).

## Data handling

The source and labeled data include MLS listing IDs, addresses, and full
remarks. Evaluation reports can contain extracted remark phrases. Confirm
data-use and sharing permissions before committing or distributing source
data, annotations, predictions, or reports containing listing text. The
code and this documentation can be reviewed separately from those data
artifacts.
