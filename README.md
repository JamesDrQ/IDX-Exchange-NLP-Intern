# IDX Exchange NLP

NLP pipeline built for the 2026 Fall NLP Intern program at IDX Exchange.

## Week 3: entity extraction

Week 3 implements a frozen, rules-based `EntityExtractor` for five entity
labels: `BEDROOM`, `BATHROOM`, `SQFT`, `PRICE`, and `AMENITY`. It extracts exact
text offsets, using regular expressions for numeric property facts and the
Week 1 taxonomy plus a limited supplemental feature list for amenities. The
extractor is implemented in [`scripts/entity_extractor.py`](scripts/entity_extractor.py),
with `scripts/annotation_helper.py` as its shared candidate interface.

### Data preparation and evaluation

The data artifacts represent different stages and must not be treated as one
fully human-verified set:

| Artifact | Size | Provenance and status |
| --- | ---: | --- |
| `week3_auto_labels.jsonl` | 250 remarks | Regex-generated predictions. All are suggestions; none are marked human-verified. |
| Development split | 30 remarks | Fixed-seed split. Compared with a separate 30-record AI-reviewed annotation file; this reference is provisional, not human-verified ground truth. |
| Local held-out test annotations | 30 remarks | Separate frozen split. The current file has 10/30 `human_verified` records, so strict evaluation is blocked. |
| Teammate gold test | 21 remarks | Separate teammate-provided dataset; all 21 carry `verified: true`. Labels are mapped in memory for scoring. These are not annotations personally verified by the user. |

The preparation and review scripts are `scripts/prepare_week3_samples.py`,
`scripts/prepare_week3_annotations.py`, `scripts/generate_week3_labels.py`,
`scripts/split_week3_data.py`, `scripts/prepare_week3_dev.py`, and
`scripts/interactive_annotator.py`. Their existing output guards prevent
accidentally replacing prior annotations or split files.

Run the development comparison with:

```bash
python -m scripts.evaluate_week3_dev
```

Run the teammate-provided 21-record comparison with:

```bash
python -m scripts.evaluate_week3_teammate_gold
```

The latter reads only `data/labeled/week3_teammate_gold_test_21.jsonl`, checks
that all 21 records are verified, checks the frozen extractor fingerprint,
and writes `data/labeled/week3_teammate_gold_test_21_evaluation.json`. It does
not alter gold labels or offsets. The separate
`scripts/evaluate_week3_test.py` evaluator is for the local 30-record held-out
split; it refuses to score while any record remains unverified.

Both reported evaluations use strict exact-span-and-label matching. A boundary
mismatch counts as a false positive and a missed gold span. The development
evaluator applies documented in-memory exclusions to AI-reviewed references;
the annotations themselves remain unchanged.

### Results and limitations

| Dataset | Records | Reference | F1 | Interpretation |
| --- | ---: | --- | ---: | --- |
| Development | 30 | AI-reviewed spans with transparent in-memory exclusions | **71.1%** | Provisional and optimistically biased because development examples were used to develop the extractor. |
| Teammate-provided test | 21 | Teammate gold annotations, mapped to the five-label schema | **37.8%** | Separate data from the local 30-record held-out split; audit found likely incomplete AMENITY coverage and inconsistent span boundaries. |

The **85% test F1 target has not been met**. The 37.8% result should be read
with the teammate reference's limitations: a seed-42 audit of five records
found likely omitted AMENITY spans, inconsistent span boundaries, and some
genuine regex errors (for example, matching `spa` where surrounding language
signaled a style rather than an installed feature). The audit was diagnostic only; it did
not change the extractor, tune against test remarks, or edit annotations.
Coverage decisions for ordinary rooms and broad feature descriptions remain
judgment calls without a more explicit AMENITY annotation policy.

The local 30-record held-out evaluator currently stops with 20/30 records
unverified. The teammate 21-record result is reported separately and does not
replace or complete that local held-out evaluation.

### Tests

Run the Week 3 tests with:

```bash
python -m unittest tests.test_week3_annotation tests.test_week3_entity_extractor tests.test_week3_interactive_annotator tests.test_week3_test_workflow
```

All 25 Week 3 tests pass in the current environment. Full unittest discovery
also runs those 25 tests but cannot import `tests/test_setup.py` and
`tests/test_week2.py` because `mysql.connector` and `pytest` are not installed.

### Data handling

The source and labeled data contain MLS listing identifiers, addresses, and
full remarks. Check data-use and sharing permissions before committing or
distributing those artifacts. Reports may also contain extracted remark text;
prefer committing code and documentation without raw listing data unless
sharing is authorized.

See [`docs/week3_regex_development.md`](docs/week3_regex_development.md) for
the implementation notes, score details, and development annotation caveats.

## Week 6: listing signal extraction

Week 6 reads listing records from `real_estate.rets_property`, applies the
read-only `SignalExtractor`, and exports one JSON object per listing. The
export includes `listing_id`, complete `remarks` (empty when missing),
`source_fields`, and the existing `signals` structure. Row-level extraction
failures are retained as JSONL records with an `error` field. Processing uses
bounded database batches and replaces the output atomically only after the
export is complete.

Configure database access with `IDX_MYSQL_USER` and `IDX_MYSQL_PASSWORD` (or
the existing `MYSQL_*` / `DB_*` environment aliases); host and port can be
set with `IDX_MYSQL_HOST` and `IDX_MYSQL_PORT`. If credentials are not set,
the existing interactive username/password prompts are used. Do not commit
credentials or raw listing exports.

Run a 100-row smoke test:

```bash
python -m scripts.process_week6_listings --limit 100
```

Process the full table:

```bash
python -m scripts.process_week6_listings
```

Both commands write `data/processed/week6_listing_signals.jsonl`. Use
`--batch-size 500` to choose a different fetch size, or `--output PATH` to
write elsewhere. A successful run prints processed, extraction-error, and
missing-Remarks counts. No full-table processing count is claimed until the
command has run against the configured database.

Evaluate a completed review CSV with strict exact-label scoring (the default)
or compare the documented canonical aliases as well:

```bash
python -m scripts.evaluate_week6_gold --input data/processed/week6_final_holdout_review.csv --normalization both
```

See [`docs/week6_final_report.md`](docs/week6_final_report.md) for Week 6
results, limitations, and annotation provenance.
