# Week 8: minimal human reference annotation

> Submission status: see `week8_final_report.md` and `week8_submission_audit.md` for current results and files. Held-out evaluation is complete (Hybrid 0.368893, below 0.4). The current reviewed references and accepted AI replacement ratings are in `data/annotations/week8_review/`. Earlier preparation commands, pending-work statements and test counts below describe their original project stage; do not recreate the freeze or regenerate test predictions.

## Two edits per listing

Open `data/annotations/week8_review/test30_references.csv` for the remaining
held-out annotation work. Edit these two columns:

1. Write your own 2–3 sentence summary in `reference_summary`.
2. Check it against the source and set `reference_status` to `human_verified`.

Save the CSV. **Nothing else needs to be entered.** Names, dates, provenance and independence fields have been
removed from the review sheets and are not required by the evaluator.

Listing IDs, original remarks, price, city, beds/baths evidence, amenities and
missing-data information remain available in gray reference columns. Existing
notes are retained for reference but do not need to be filled in. Source facts
are grouped in `source_facts`; bedrooms/bathrooms may be quoted phrases rather
than verified totals because the export lacks structured count columns.

Keep the supplied IDs and source columns unchanged. Include supported beds,
baths, price, location and up to two notable features when available. Omit facts
that are missing or ambiguous. Distinguish private/community pools, main/guest
units and proposed/existing features. Do not copy generated summaries into your
reference. If unfinished, leave the status pending or optionally use
`human_authored` or `needs_resolution`.

## Files and preservation

The existing review order remains: three batches of 10 development listings,
then all 30 test listings. The original 70/30 dataset split and all IDs are
unchanged. The other 40 development records remain in the original dataset.

CSV alternatives are `data/annotations/week8_review/dev30_references.csv` and
`test30_references.csv`. Use either the workbook or CSV, not two edited copies.
The evaluator reads either format directly.

The original Step 1 annotation files remain unchanged. Copies of both previous
workbooks, both CSVs and their preparation metadata are retained under
`data/annotations/week8_review/backups/before_minimal_workflow/`, with hashes in
`backup_manifest.json`. Removed metadata has not been discarded. Existing summary
text, statuses, notes and source information were preserved during migration.
The separate teammate-rating workbook is unchanged.

## Evaluation eligibility and held-out protection

A row is eligible only when its `reference_summary` is nonempty after trimming
whitespace and its `reference_status` is `human_verified`. All other statuses and
empty summaries are ignored and counted. Legacy metadata columns, if present,
are optional and do not change eligibility. No dates or author names are inferred
or fabricated. File hashes and sample counts are recorded automatically.

Development evaluation can use any approved subset. Held-out test evaluation
still requires **all 30 test IDs with nonempty, human_verified references**, plus
a matching explicit model freeze file. The evaluator checks those gates before
loading test prediction text. Duplicate/wrong-split IDs, stale predictions or
changed freeze hashes are errors. Generated prediction files cannot be used as
reference files, and predictions never fill missing reference text.

The current Step 5A freeze binds the final evaluator implementation. Do not use
an older lock or silently recreate the current lock after a code change.

ROUGE-L uses Unicode NFKC normalization, case folding, alphanumeric tokens,
no stemming, and document-level longest common subsequence. It reports the
unweighted mean F1 and the same approved sample count for lead-2, extractive and
hybrid predictions. No approved references yields a null mean, not zero.
Development and test scores remain separate.

## Frozen candidate and current files

Step 5A has frozen the selected **Hybrid** method at development ROUGE-L F1
**0.41903472547172027**. Lead-2 and extractive remain comparison methods.
The corrected development CSV was used. The user confirms the current development
references are human-authored; earlier drafting history remains in the historical
reports. No provenance flags were automatically certified.

Use the CSV files as the current annotation source of truth:

- Development (complete): `data/annotations/week8_review/dev30_references.csv`.
- Held-out test: `data/annotations/week8_review/test30_references.csv`.

At freeze preparation, all 30 test references were blank and
`pending_human_authoring`. IDs and source remarks match the frozen test records.
The old XLSX files are alternatives, not synchronized copies of the updated CSVs.
Do not switch to an older workbook and accidentally discard reviewed content.

Write each test reference using only its original remarks and source facts.
Enter 2–3 concise sentences, then set `reference_status=human_verified` after
checking every claim. Those are the only required edits. Preserve listing IDs,
source columns and any existing notes. Do not view generated test summaries while
writing references. Do not generate references with the summarizer. If any content
is AI-assisted, preserve that history in optional notes or a separate provenance
record; human verification does not imply independent human authorship.

## Frozen artifacts

- Predictions: `data/processed/week8_summaries_frozen/` (70 dev, 30 test).
- Evaluator lock: `data/processed/week8_eval/model_freeze.json`.
- Selected method, runtime/configuration and full hashes:
  `data/processed/week8_eval/candidate_release.json`.
- Source code, taxonomy and tokenizer snapshots:
  `data/processed/week8_eval/frozen_candidate/`.
- Reproduced development result:
  `data/processed/week8_eval/dev_freeze_verification.json`.

Do not edit or regenerate the frozen candidate. The evaluator checks the current
code, taxonomy and dataset against the generation manifest, and checks both
prediction hashes, the run manifest, dataset manifest, evaluator and normalization
against the freeze lock. Source snapshots and runtime/tokenizer hashes support
reproduction. This is an integrity lock, not filesystem write protection.

## Held-out evaluation command — not run yet

Only after **all 30 test references are nonempty and human_verified**, run from
the repository root. This command uses the frozen prediction directory explicitly;
the default directory contains older predictions.

```bash
conda run -n idx-nlp python -m scripts.evaluate_week8_rouge evaluate \
  --split test \
  --references data/annotations/week8_review/test30_references.csv \
  --prediction-dir data/processed/week8_summaries_frozen \
  --freeze-file data/processed/week8_eval/model_freeze.json \
  --output data/processed/week8_eval/test_rouge_frozen.json
```

The output filename must be new. The evaluator does not overwrite annotations or
predictions. Incomplete references, duplicate/wrong-split IDs, stale code/data or
freeze-hash mismatches stop evaluation. Test prediction text is loaded only after
the completeness and freeze gates pass. Do not recreate a freeze to bypass a
mismatch; investigate the changed artifact. Real held-out evaluation has not run.

## Teammate review of 20 frozen Hybrid summaries

Use `data/annotations/week8_review/teammate_ratings20_frozen.csv`. The earlier
`teammate_ratings20.csv` is preserved but contains pre-optimization summaries.
The refreshed sheet uses the same 20 development IDs and source evidence, with
frozen Hybrid summaries. All rating and comment cells are blank.

For each row, read the original remarks and source facts, then enter integer
scores in `factual_accuracy`, `completeness`, `readability`, and `conciseness`.
Add `comments` for unsupported claims, omissions, confusing scope or awkward text.
Names/dates are optional; `rating_status` may be set to `completed` after all four
scores are entered. Do not replace blanks with zero or AI-generated ratings.
Use one shared file, or separate copies per teammate if multiple ratings per
summary are wanted. Do not overwrite one teammate's ratings with another's.

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Factual accuracy | Major unsupported/contradictory claims | Some ambiguous or inaccurate details | Every claim supported, including condition and scope |
| Completeness | Most important available facts missing | Main facts covered, meaningful omissions | Key facts and distinctive features well represented |
| Readability | Difficult to understand | Understandable with awkward phrasing | Clear, natural, grammatical |
| Conciseness | Very repetitive or poorly focused | Some unnecessary wording | Focused, compact, no unnecessary repetition |

Use 2 and 4 for intermediate quality. Judge completeness only against information
actually available in the listing. A short summary can score well for conciseness
and poorly for completeness. These are human judgments, not ROUGE estimates.
Teammates should not edit reference summaries to resemble the predictions.

## Tests

The tests exercise minimal three-column reference files, optional legacy metadata,
empty/unreviewed references, synthetic ROUGE calculations, unchanged held-out
completeness/freeze gates, and rejection before test prediction text is loaded.
They also verify annotation/source preservation, output guards and workbook/CSV
source-data agreement. Successful test scoring in automated tests uses temporary
synthetic fixtures only.
