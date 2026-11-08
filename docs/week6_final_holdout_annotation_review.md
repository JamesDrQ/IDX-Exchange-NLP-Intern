# Week 6 Final Holdout Annotation Review

## Completion

- Annotated all **100** rows and all **17 existing `gold_*` fields** (1,700 populated cells).
- Preserved the original 100 listing IDs, order, Remarks, `source_fields_json`, prediction cells, and columns. The original file is backed up at `data/processed/week6_final_holdout_review_backup.csv`.
- All 100 `review_status` values remain `pending`; all rows are AI annotations awaiting human review.
- Numeric entities use numeric strings or `unknown`; flags use only `true`, `false`, or `unknown`; every keyword/amenity cell is a valid JSON array of strings.

## Gold completion profile

| Field | Known / labeled | Unknown / empty set |
| --- | ---: | ---: |
| Bedrooms | 78 | 22 unknown |
| Bathrooms | 71 | 29 unknown |
| Living area (sqft) | 36 | 64 unknown |
| Price | 100 | 0 unknown |
| City | 99 | 1 unknown |
| Pool flag | 89 | 11 unknown |
| Private pool flag | 68 | 32 unknown |
| Community pool flag | 89 | 11 unknown |
| Garage flag | 96 | 4 unknown |
| Fireplace flag | 61 | 39 unknown |
| View flag | 72 | 28 unknown |
| Condition tags | 65 non-empty arrays | 35 `[]` |
| Financial tags | 41 non-empty arrays | 59 `[]` |
| Location tags | 71 non-empty arrays | 29 `[]` |
| Property type tags | 56 non-empty arrays | 44 `[]` |
| View tags | 40 non-empty arrays | 60 `[]` |
| Amenity tags | 93 non-empty arrays | 7 `[]` |

An empty tag array is an explicit absence of applicable positive text labels under the annotation rules. Scalar `unknown` values remain unknown rather than being treated as false.

## Consistency and validation

- Used canonical category vocabulary from the project taxonomy, the active amenity inventory, and documented supplemental labels; applied the synonym rules in `docs/week6_annotation_guidelines.md`.
- Checked that every keyword and amenity value is a JSON array of strings and each array label belongs to the documented inventory or canonical alias list.
- Checked numeric/city entity formats and the three-value flag vocabulary.
- Checked all IDs are unique and row order matches the backup.
- Verified programmatically that listing IDs, full Remarks, source fields, and every `pred_*` cell exactly match the pre-edit backup. No prediction contents were consulted to choose labels and no prediction-versus-Gold comparison or evaluation was run.
- No extractor, entity extractor, taxonomy, or evaluator files were changed.

## Cases needing special human review

All 100 rows need human review before changing their status from `pending`. These records have a specific uncertainty, source conflict, scope decision, or interpretation documented in `reviewer_notes`:

`1191009008`, `1182474425`, `1176374768`, `1188655273`, `1158794809`, `1177653126`, `1174209727`, `1173672595`, `1187538118`, `1189355881`, `1175356448`, `1177996070`, `1176225463`, `1183440819`, `1190386450`, `1190815478`, `1152132850`, `1174221287`, `1181369338`, `1190319533`, `1183655004`, `1189347125`, `1190598483`, `1159456015`, `1111717970`, `1182414634`, `1179567970`, `1183699791`, `1172029864`, `1178500347`, `1182480319`, `1189772230`, `1177097847`, `1173665765`, `1179300604`, `1155797232`, `1178000697`, `1182194443`, `1189332745`, `1152543533`, `1175214840`, `1189218744`, `1189775595`, `1190989641`, `1190868670`, `1154361071`, `1183447590`, `1177033326`, `1190465820`, `1170462838`, `1179441017`, `1177240889`, `1191038842`, `1175188615`, `1191032026`, `1174229612`, `1178610902`, `1178215407`, `1191002446`, `1175185988`, `1183993128`, `1191021555`, `1175554809`, `1179064657`, `1179342300`, `1155423316`, `1189560705`, `1182387770`, `1176201228`, `1176663048`, `1178684603`, `1189429592`, `1168596457`, `1190317005`, `1173189825`, `1190152445`.

Priority ambiguity groups:

- **Pool source conflicts or three-valued status:** `1176374768`, `1158794809`, `1189355881`, `1111717970`, `1182414634`, `1183699791`, `1182480319`, `1178500347`, `1182194443`, `1190152445`, `1179342300`, `1189429592`, `1176201228`, `1176663048`. In particular, `PoolPrivateYN=1` with community-type features/text needs checking; where community is supported but private status has no explicit evidence, private-pool is `unknown`. A listing with explicit private and community pool tokens is labeled as both, pending review.
- **Unit/count/area scope:** `1191009008`, `1182474425`, `1187538118`, `1188655273`, `1177996070`, `1175356448`, `1181369338`, `1190598483`, `1159456015`, `1175188615`, `1178215407`, `1175185988`, `1183993128`, `1175554809`, `1189560705`, `1183447590`. These include duplex/ADU totals, conversion options, missing bath or living-area totals, and separate-unit scope.
- **Conflicting or absent structured feature flags:** `1183655004` (garage flag/source parking conflict), `1155797232` (fireplace feature tokens conflict), `1177033326` (fireplace text versus `None` feature token), `1170462838` (pool boolean without text amenity), `1177240889` (association pool appears in fields but not Remarks), `1179064657` (Remarks empty), `1189218744` (carport versus garage), `1190989641` (approximate area and unknown bath count).
- **Property/type and amenity boundary decisions:** `1182474425` (vacant-lot/build alternative), `1183440819` (separate studio-style unit and unusable dock/pier/lift), `1182414634` (private-pool interpretation), `1189560705` (primary dwelling type), `1152543533` (“family lodge”), `1175214840` (nearby playground), `1155423316` (rooftop spa and view/amenity mapping), `1191002446` (EV outlet versus charger), `1191032026` (optional solar), `1183447590` (repair-required waterfront facilities).

The complete row-specific evidence notes remain in the CSV so a reviewer can inspect the exact concern alongside each listing.

## Policy summary

Structured source values are preferred for price, city, numeric facts, and reliable booleans. Missing fields do not imply false. Community pools do not imply private pools; private-pool and community-pool flags are assessed independently. `PoolFeatures="None"` is treated as the project’s explicit no-pool sentinel unless stronger listing evidence conflicts. Text labels come from the Remarks and use the project’s canonical terms. Synonyms are normalized; nearby public facilities are location signals, not property amenities; community facilities are amenities only when described as included/resident-accessible. Negated, proposed, optional, or unusable features are not labeled as existing positives. Unresolved conflicts stay unknown and are called out for human review.

## Evaluation status

No evaluation was run and no accuracy or F1 result is claimed. The evaluation script only includes rows marked `done`, `verified`, or `yes`; once human review is complete, evaluate the reviewed subset with:

```bash
python -m scripts.evaluate_week6_gold --input data/processed/week6_final_holdout_review.csv
```
