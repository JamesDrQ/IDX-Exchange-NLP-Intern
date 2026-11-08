# Week 6 Gold Annotation Review

## Annotation status

Annotated all **30 of 30 listings**, filling all **17 gold fields per listing** (510 values). Every row remains `review_status=pending`; no row is human-verified. Gold labels are AI-generated working annotations and must not be treated as measured extraction accuracy.

The backup is `data/processed/week6_gold_review_backup.csv`. Original row order, 39-column schema, listing text, source JSON, and prediction values were checked against it.

## Gold completion statistics

Scalar entities use `unknown` when evidence does not establish a single value. Tag columns contain JSON arrays, with `[]` for no supported labels.

| Field | Known values / distribution | Unknown |
|---|---:|---:|
| `gold_entity_bedrooms` | 17/30 known | 13 |
| `gold_entity_bathrooms` | 14/30 known | 16 |
| `gold_entity_sqft` | 6/30 known | 24 |
| `gold_entity_price` | 30/30 known | 0 |
| `gold_entity_city` | 30/30 known | 0 |
| `gold_flag_pool` | true 13, false 14, unknown 3 | — |
| `gold_flag_private_pool` | true 3, false 22, unknown 5 | — |
| `gold_flag_community_pool` | true 9, false 16, unknown 5 | — |
| `gold_flag_garage` | true 24, false 4, unknown 2 | — |
| `gold_flag_fireplace` | true 19, false 1, unknown 10 | — |
| `gold_flag_view` | true 20, false 1, unknown 9 | — |

For each keyword and amenity array, all 30 rows are annotated (including explicit empty arrays).

## Prediction versus gold differences

All 30 listings have at least one difference between prediction and gold. Differences are not accuracy results; they include evidence-based corrections, legitimate unknowns, normalization choices, and decisions to omit nearby or hypothetical features.

Field-level difference counts:

| Field | Rows with a difference |
|---|---:|
| `entity_bathrooms` | 1 |
| `entity_bedrooms` | 2 |
| `entity_sqft` | 1 |
| `flag_community_pool` | 17 |
| `flag_fireplace` | 1 |
| `flag_garage` | 0 |
| `flag_pool` | 14 |
| `flag_private_pool` | 22 |
| `flag_view` | 3 |
| `tags_amenities` | 22 |
| `tags_condition` | 19 |
| `tags_financial` | 5 |
| `tags_location` | 13 |
| `tags_property_type` | 7 |
| `tags_view` | 1 |

Listing IDs with differences:

- `1157717300`: flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_view, tags_amenities
- `1187242554`: flag_private_pool, tags_location, tags_property_type, tags_amenities
- `1178534984`: flag_pool, flag_private_pool, flag_community_pool, tags_financial, tags_amenities
- `1157424518`: tags_condition, tags_amenities
- `1168582881`: tags_condition, tags_financial, tags_location
- `1176633762`: flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_location, tags_amenities
- `1176770777`: flag_pool, flag_private_pool, flag_community_pool, tags_condition
- `1190710621`: flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_location, tags_property_type, tags_amenities
- `1176389519`: flag_private_pool, tags_condition, tags_amenities
- `1176776552`: entity_bedrooms, entity_bathrooms, entity_sqft, flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_property_type, tags_amenities
- `1176661812`: flag_community_pool, tags_amenities
- `1188703577`: flag_private_pool, tags_condition
- `1189502345`: flag_private_pool, tags_location, tags_property_type, tags_amenities
- `1190978841`: tags_condition, tags_location, tags_property_type, tags_amenities
- `1190408434`: flag_private_pool, tags_condition, tags_location
- `1190311232`: flag_pool, flag_private_pool, flag_community_pool, tags_location, tags_amenities
- `1151200509`: tags_location, tags_property_type, tags_amenities
- `1190157585`: flag_pool, flag_private_pool, flag_community_pool, tags_condition
- `1185646501`: flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_amenities
- `1184027849`: flag_private_pool, flag_view, tags_condition, tags_financial, tags_property_type, tags_amenities
- `1180000367`: tags_amenities
- `1174677467`: flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_amenities
- `1178101629`: flag_private_pool, flag_view, tags_financial, tags_amenities
- `1173196067`: flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_location
- `1167320852`: flag_pool, flag_private_pool, flag_community_pool, tags_condition, tags_location, tags_amenities
- `1177430194`: flag_pool, flag_private_pool, flag_community_pool, tags_condition
- `1188070721`: flag_pool, flag_private_pool, flag_community_pool, tags_amenities
- `1190554152`: flag_private_pool, flag_community_pool, flag_fireplace, flag_view, tags_location, tags_amenities
- `1176048187`: flag_community_pool, tags_condition, tags_location
- `1154270309`: entity_bedrooms, tags_financial, tags_amenities

### Possible false positives and false negatives

These are review leads, not adjudicated error counts. For exact set comparison, prediction-only labels are possible false positives and gold-only labels are possible false negatives.

| Label set | Prediction-only labels (possible FP) | Gold-only labels (possible FN) |
|---|---:|---:|
| condition | 7 | 24 |
| financial | 1 | 4 |
| location | 5 | 11 |
| property_type | 2 | 5 |
| view | 0 | 1 |
| amenities | 38 | 20 |

Patterns to inspect include:

- Pool predictions where a pool is only available through a community/association, and missed community-pool labels when remarks say community, HOA, or association pool.
- `private_pool` predictions when remarks mention only a community pool; a generic pool mention does not prove private ownership.
- Amenity matches framed as possibilities or referring to nearby public or community facilities rather than a property feature.
- Broad keyword matches such as `studio` for a room’s possible use and `view` from generic scenic phrasing.
- Missed supported condition, financing, and location phrases, including repair-needed/TLC, seller financing, and natural-language variants not covered by taxonomy terms.

## Uncertain cases for manual verification

- `1176776552`: Remarks give a 1,890–2,550 sq. ft. plan range and up to five bedrooms/three baths; this specific unit’s values are not resolved.
- `1176633762`: Pool and gym access is described as available for a separate membership fee; review amenity inclusion/access policy.
- `1151200509`: Remarks establish pool and spa, but source identifies pool features without an explicit private-pool flag; garage data is missing.
- `1190978841`: Pool/private/community status is absent from the source fields and remarks.
- `1190311232`: Pool and outdoor kitchen are presented as possibilities to create, not existing features; annotated as absent/omitted.
- `1154270309`: Bedroom count says “6-bedroom (?)” and the estate contains multiple dwellings; main-house count remains unknown. Pool ownership is not specified.
- `1180000367`: Structured data marks both private and association pool features; remarks confirm a private pool and community amenities, so review both labels.
- `1177430194`: Remarks mention a detached bonus room with possible uses including “studio”; it is not labeled as an existing studio property type.

The discrepancy list identifies additional rows to check. Because every row has at least one differing field, **all 30 listing IDs merit manual review** before changing any status to `done`.

## Pipeline recommendations

1. Keep private, community/association, and general pool signals separate; combine remarks with `PoolFeatures` and `PoolPrivateYN` without inferring ownership from generic pool mentions.
2. Treat phrases framed as plans, possibilities, or nearby access as non-present amenities unless the listing asserts the feature currently exists at the property.
3. Preserve scalar uncertainty for range statements and unclear counts; consider a structured range/ambiguous state if these cases need evaluation.
4. Expand phrase normalization for common listing language (TLC/fixer, seller financing, “half-hour from,” “newly installed”) and normalize close taxonomy variants consistently.
5. Add targeted checks for `ViewYN` and descriptive views so a view label requires supported property evidence, while retaining explicit database flags.
6. Add extraction review cases for room-use terms (`studio`, `office`, `loft`) and amenities mentioned only as community benefits or possible improvements.

## Validation performed

- Confirmed 30 rows, original order, unchanged non-gold content, and unchanged columns.
- Confirmed all 30 rows remain pending.
- Parsed every scalar with the evaluator’s entity/flag parsers and every tag field as a JSON array of strings.
- Ran `python3 -m scripts.evaluate_week6_gold`; it parsed the file and reported **0 reviewed of 30**, as expected while all rows are pending. No accuracy is reported.
