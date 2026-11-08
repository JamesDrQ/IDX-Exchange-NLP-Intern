# Week 6 Independent Holdout Annotation Review

## Annotation status

Annotated all **50 of 50** listings and populated all **17 Gold fields per row** (850 values). Every row remains `review_status=pending`. These are AI-assisted working annotations and are not human-verified.

The original 39-column schema, row order, listing IDs, remarks, source fields, and prediction cells were preserved. A pre-edit copy is available at `data/processed/week6_holdout_review_backup.csv`.

No prediction values or development Gold Labels were consulted to make annotations. No evaluation or prediction-to-Gold comparison was run.

## Completion counts

Scalar fields use `unknown` where the remarks and structured fields do not establish a value. Keyword and amenity columns contain JSON arrays, including `[]` where no applicable label was supported.

| Gold field | Known / true | False | Unknown |
|---|---:|---:|---:|
| `entity_bedrooms` | 39 known | — | 11 |
| `entity_bathrooms` | 36 known | — | 14 |
| `entity_sqft` | 15 known | — | 35 |
| `entity_price` | 50 known | — | 0 |
| `entity_city` | 50 known | — | 0 |
| `flag_pool` | 28 true | 19 | 3 |
| `flag_private_pool` | 7 true | 40 | 3 |
| `flag_community_pool` | 24 true | 20 | 6 |
| `flag_garage` | 41 true | 5 | 4 |
| `flag_fireplace` | 34 true | 16 | 0 |
| `flag_view` | 33 true | 12 | 5 |

All six keyword/amenity columns across 50 rows (300 arrays total) are populated and parse as JSON arrays of strings. Keyword labels were checked against the project taxonomy and the documented extractor labels.

## Cases for human verification

- `1174059220`: Remarks say “nearly 1,000 sq. ft.” and describe a loft-style residence without an explicit bedroom count. I recorded 1,000 as the numeric approximation and left bedrooms unknown.
- `1190033644`: The structured pool feature is `Association`; remarks describe Sun & Sail Club membership across the street and recreation/swimming access. Confirm that this association pool counts as a pool associated with the listing.
- `1191028821`: Remarks describe a rebuilt backyard pool, while structured fields provide `InGround` but leave private-pool status blank. Private ownership is inferred from the pool being part of the home's backyard.
- `1191040489`: The listing is a duplex with two residences, each described as 3 bedrooms and 2.5 baths. Listing-level bedroom/bathroom totals and square footage are not stated, so those values remain unknown.
- `1170307787`: The 3.5-bath count is inferred from the primary suite bath, main-level en-suite, and shared downstairs bath. Verify the total against the intended listing-level convention.
- `1155730692`: The remarks describe a 3-bedroom, 3-bath property and views over a greenbelt, but do not describe a pool. Structured pool fields are null, so pool flags remain unknown.
- `1172448599`: Remarks give “1 Master Br” and total area including balcony; the bathroom count and living-area square footage are not established. The rooftop pool and other amenities are building/community facilities.
- `1176684731`: Remarks describe a backyard “spool” and spool equipment; structured pool features identify community/association access. I labeled both private and community pools true, but the meaning and ownership of “spool” merit review.
- `1190942937`: `PoolPrivateYN=1` indicates a private pool while `PoolFeatures=Association` and remarks mention community pool access. I labeled both pool types true; verify that the structured fields refer to separate facilities.
- `1158228212`: The property contains a two-bedroom cottage and a separate one-bedroom ADU; the stated area is 3,300+ sq. ft. Aggregate bedroom, bathroom, and square-foot values are unclear, so those counts remain unknown.
- `1160016554`: Remarks describe pool access through an optional country-club membership, while structured features say `Community,Association`. Confirm whether the separately accessed club pool belongs in community-pool labels.
- `1190329465`: `PoolFeatures=Association` is the only pool evidence; remarks mention community laundry but no pool. Pool flags are labeled from the structured feature and should be checked against the source-field convention.
- `1169561375`: The structured record has both `PoolPrivateYN=1` and `Community`/`Private` pool features, and remarks describe a custom pool at the home. Both private and community pool are labeled true.
- `1183165813`: The remarks identify a 4-bedroom/4-bath home plus a permitted JADU with an additional bathroom. The total bathroom count depends on whether the label should include the accessory unit, so it remains unknown.
- `1156425317`: The property has a lakefront dock and beach area for swimming, but no pool; `PoolFeatures=None`. The pool flags are false. Confirm that lake swimming is not treated as a property pool under the project rubric.

Other `unknown` values reflect absent numeric facts or null structured fields. Please review all rows before changing any status to `done`.

## Manual review and evaluation

Review the complete remarks and source fields in `week6_holdout_review.csv`, correct any labels, and change `review_status` to `done` only for rows you have verified. Then run:

```bash
python -m scripts.evaluate_week6_gold --input data/processed/week6_holdout_review.csv
```

This 50-row sample is intended as an independent holdout. Keep its labels and results separate from development-set tuning.
