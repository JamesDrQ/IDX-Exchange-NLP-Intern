# Week 8 reference-summary guidelines

Use the current minimal workflow in `docs/week8_annotation_workflow.md`.
Open `outputs/week8_step4a/dev30_references.xlsx` and then
`outputs/week8_step4a/test30_references.xlsx`.

## Only two manual fields

1. `reference_summary`: write your own concise 2–3 sentences.
2. `reference_status`: set to `human_verified` after checking factual accuracy.

Reviewer names, review dates, provenance, independence fields and verification
notes are not required. Existing legacy fields remain preserved in the original
files and migration backups; the evaluator ignores them for eligibility.

## Writing a reference

Read original remarks and structured source fields. Include beds, baths, price,
location and up to two supported notable features when available. Aim for clear,
concise wording, usually 35–70 words. Do not invent unavailable information or
manufacture a second feature. Do not copy a generated model summary.

Verify bedroom/bathroom scope carefully: the existing export has no structured
count totals, and remarks may describe multiple dwellings, ranges, or full/half
components. Do not turn missing values into zero. Preserve distinctions between
private/community pools and existing/proposed amenities. Source-extracted phrases
are reading aids, not human-verified labels. Avoid disputed assertions when source
fields and remarks conflict.

Leave unfinished rows pending, or optionally use `human_authored` or
`needs_resolution`. Only nonempty summaries marked `human_verified` enter ROUGE.

## Dataset and evaluation

The frozen split remains 70 development / 30 held-out test listings. The initial
review packets contain 30 prioritized development records and all 30 test records.
Existing listing IDs and original annotation files are unchanged. The other 40
development records remain available in the original infrastructure.

Keep reference writing independent of generated summaries. Test evaluation is
blocked until all 30 test references are approved and an explicit model freeze
matches the predictions, dataset and evaluator. Do not tune on held-out results.

The separate requirement for teammates to rate 20 generated summaries is a later
review task. Its template is unchanged by this reference-workflow simplification.
