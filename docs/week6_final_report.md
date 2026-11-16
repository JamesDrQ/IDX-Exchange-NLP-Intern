# Week 6 Final Report: Listing Signal Extraction

## Objective and architecture

Week 6 extracts structured property signals and normalized free-text labels
from real-estate listing records. The pipeline has three parts:

1. `scripts.process_week6_listings` reads `real_estate.rets_property` in bounded
   batches and writes a JSONL record for each listing.
2. `SignalExtractor` combines database fields with full Remarks and delegates
   numeric/entity parsing to `EntityExtractor`.
3. `scripts.evaluate_week6_gold` compares predictions to reviewed CSV labels.
   It reports strict exact-label scores by default and offers a documented,
   symmetric canonical normalization mode for policy-approved synonyms.

The batch runner is inference-only and does not write to the database. Each
successful JSONL record contains the listing ID, Remarks, source fields, and
the established signal schema. Missing Remarks are represented as an empty
string. A row-level extraction error is recorded on that listing and does not
stop later rows. The output is first written to a temporary file in the target
directory and atomically replaced on successful completion.

## Evaluation results

| Dataset | Structured accuracy | Free-text strict micro-F1 | Free-text canonical micro-F1 |
| --- | ---: | ---: | ---: |
| Development | 99.2% | 90.6% | Not reported |
| Final holdout, 100 listings | 97.2% | 64.7% | 65.5% |

Canonical normalization reconciled 12 false-positive and 12 false-negative
label instances on the final holdout, primarily documented spelling,
hyphenation, and synonym variants in property type and amenities. The strict
score remains available and is the evaluator default. Canonical scoring is
not a substitute for strict scoring and does not change the prediction or
Gold Label files.

The free-text result remains below the 75% reference target. The current
holdout results should be treated as diagnostic estimates rather than proof of
generalization. Development data were used during implementation; the holdout
has already been used for analysis and is no longer an untouched final test.

## Data processing status

The full-table batch completed and wrote
`data/processed/week6_listing_signals.jsonl`. A streaming validation found:

| Check | Result |
| --- | ---: |
| JSONL records / source rows exported | 55,212 |
| Successful extraction records | 55,212 (100%) |
| Per-listing extraction failures | 0 |
| Valid JSON lines | 55,212 / 55,212 |
| Unique nonempty Listing IDs | 55,209 |
| Missing Listing IDs | 0 |
| Records with missing Remarks | 321 (0.58%) |
| Records with complete required signal schema | 55,212 / 55,212 |

The source query selects rows with a non-null Listing ID, so 55,212 describes
the exported eligible rows; rows with a null Listing ID are outside this
export's scope. Three Listing IDs each appear twice. In every case, the
repeated JSONL lines are byte-for-byte identical, indicating duplicate source
rows in the selected result. They were retained; no records were silently
removed or deduplicated during report validation. The generated JSONL remains
ignored by Git because it contains raw listing data and full Remarks.

Smoke test locally with:

```bash
python -m scripts.process_week6_listings --limit 100
```

Full-table execution:

```bash
python -m scripts.process_week6_listings
```

## Limitations and annotation provenance

- Final holdout free-text F1 is below the 75% reference target, even after
  canonical normalization.
- Remaining mismatches include broad or contextual keyword matches, omitted
  synonyms, differences in label coverage and specificity, and genuine
  extraction misses. The current scores do not isolate those causes fully.
- The development and holdout datasets are small relative to the full table.
- **The final holdout labels were LLM-reviewed and are not independently
  human-verified.** Their scores are provisional and must not be presented as
  independently verified accuracy.

The engineering deliverable is complete without another tuning cycle. The
local full-table export validated with zero extraction and serialization
errors. The three duplicated source rows remain a data-quality caveat for
downstream analyses that assume one record per unique Listing ID.
