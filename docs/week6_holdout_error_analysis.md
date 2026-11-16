# Week 6 Holdout Error Analysis

## Scope and method

This analysis compares the existing predictions and reviewed Gold Labels in the 50-row holdout and 30-row development CSVs. It uses the current evaluator's exact-label set comparison (case-folding and trimming, with no synonym, punctuation, singular/plural, or specificity normalization). Structured flag and entity fields are compared as stored. No CSV, Gold Label, prediction, extractor, taxonomy, or evaluator was changed.

The reported keyword counts below are **label-instance** false positives (FP) and false negatives (FN), not listing counts. A label can be a reasonable paraphrase of a Gold Label and still count as one FP plus one FN.

## Free-text results by category

| Category | Holdout FP | Holdout FN | Holdout micro-F1 | Development FP | Development FN | Development micro-F1 |
|---|---:|---:|---:|---:|---:|---:|
| Condition | 56 | 47 | 55.0% | 7 | 24 | 76.0% |
| Financial | 12 | 4 | 70.4% | 1 | 4 | 82.8% |
| Location | 75 | 45 | 43.9% | 5 | 11 | 88.2% |
| Property type | 17 | 29 | 47.7% | 2 | 5 | 87.7% |
| View keywords | 7 | 10 | 74.6% | 0 | 1 | 97.6% |
| Amenities | 294 | 213 | 51.4% | 38 | 20 | 90.0% |

The largest holdout deterioration is in amenities, location, and property type. Condition also has many errors. Financial and view keywords have smaller gaps. These category F1s use the same exact-label metric as the evaluator; the category counts sum to the reported holdout micro-F1 of approximately 52.3%.

### Condition

The extractor overmatches generic descriptive terms and overlapping phrases: `maintained` (13 FPs), `custom` (12), `modern` (7), `upgraded` (5), and `luxury` (4). Its broad substring/phrase matches can treat design or HOA descriptions as property condition, and can emit several nested condition labels for one phrase. It misses Gold labels such as `freshly painted` (9 FNs), `move in ready` (7), `updated` (7), and `well maintained` (7).

- **1190033644:** Remarks say “move-in-ready” and “fresh paint”; Gold uses `move in ready` and `freshly painted`. The extractor misses the hyphenated/near-synonym expressions. It also labels `renovated` and `maintained` from the HOA's recently renovated balconies and “well-maintained community,” although those statements do not describe the unit's condition. The same row's `PropertyCondition=Turnkey` supports the Gold `turnkey` label, which is also absent from predicted keywords.
- **1182402709:** “move-in ready homes” is explicit but missed because the phrase differs from the taxonomy spelling. This is a likely phrase-normalization/extraction miss.
- **1158228212:** `custom` and `luxury` are triggered by cabinetry/appliance descriptions. Whether these belong in *condition* is a taxonomy/annotation-scope question; `modern` is supported by “modern construction,” but overlaps with condition-like `brand new`/`modern` annotation conventions.

### Financial

The smaller error volume is largely overlapping terms and inconsistent granularity. `income` (4 FPs), `rental` (2), `hoa fees` (2), and `hoa` (2) are frequent predicted extras. The Gold misses `investment opportunity` twice, plus `rental income` and `investment` once each.

- **1170100662:** “rental income” produces `rental income`, `income`, and `rental` predictions, while Gold includes only `rental income` and `rental`. This is a nested-term/label-granularity difference, not three separate concepts.
- **1190824374:** Remarks say “rental income potential” and “investor”; predictions include `income` and `rental`, while Gold includes `rental income` and `investment`. The Gold `investment` is semantically supported, but the extractor's taxonomy does not appear to normalize “investor” to that label.

### Location

Location is a major extraction and evaluation issue. Common extras include `conveniently located` (9 FPs), `direct access` (7), `parks` (7), `just minutes` (7), `ideally located` (5), and `beach` (5). Frequent Gold-only labels include `nearby` (13), `close to` (7), `minutes from` (5), and `near shopping` (3). Exact matching treats overlapping expressions as different labels, and the Gold set often selects a smaller set of location phrases.

- **1190033644:** The remarks support `freeways` and `schools`, but also say “direct access” to a carport and patio, which is not a location signal. The model returns `direct access`, `conveniently located`, `located near`, `close to`, `freeways`, and `schools`; Gold keeps `nearby`, `freeways`, and `schools`. This shows both a false positive from non-location context and different phrase selection for the same proximity claims.
- **1179717732:** “just minutes from historic downtown Julian” triggers both `just minutes` and `minutes from`; Gold retains only `minutes from`. That is duplicate/overlapping-label behavior, not a failure to identify the destination.
- In remarks across the holdout, `beach`, `parks`, `schools`, and `freeways` sometimes denote nearby destinations, but broad terms can match a property's setting or a feature without a clear proximity relation. A phrase-level presence matcher does not reliably distinguish proximity, access, and an on-property amenity.

### Property type

Predicted extras are `loft` (6 FPs), `studio` (6), and generic `residence` (5). The largest Gold-only label is `single family home` (17 FNs), followed by `residence` (8). The extractor detects local property-type words without resolving whether they describe the whole listing, one room, or a secondary unit; Gold sometimes supplies a whole-property class from context or database knowledge that is not written as a matching phrase.

- **1179717732:** The listing is an Alpine-style cabin/cottage. `loft` describes the bedroom, and `studio` is one possible use of a storage shed. Neither describes the property type. Gold says `cottage`; predicted `loft` and `studio` are context/scope false positives.
- **1158228212:** The property is a “coastal cottage and ADU”; “private studio or workspace” describes a possible ADU use. The model emits `residence`, `cottage`, and `studio`, while Gold keeps `cottage`. `studio` is a secondary-use phrase, and `residence` is overly broad.
- **1170100662:** “studio layout” describes an attached junior ADU, while the main property is a ranch-style home. The Gold `single family home` is plausible, but the model's `studio` applies to a secondary unit rather than the listing as a whole.

The 17 `single family home` FNs need row-level review: some are likely missing synonyms or extraction failures, while others may reflect Gold labels inferred from “home” or listing context rather than a literal canonical phrase.

### View keywords

There are relatively few errors. Predictions add `view` (4 FPs) and miss `views` (4 FNs), with singular/plural and phrase-specific variations also appearing (`mountain views`, `ocean view`/`ocean views`). For example, **1175801826** has “garden views”; both sets contain `views`, but Gold says the structured view flag is false (see structured analysis below). Keyword extraction is supported by the text; the structured Gold disagreement is separate.

### Amenities

Amenities account for the most label-instance errors and errors occur in all 50 rows. Frequent predictions include `natural light` (14 FPs), `walk-in closet` (11), `primary suite` (10), and `storage` (9). Gold-only labels include `garage` (14), `kitchen` (10), `community pool` (8), `balcony` (8), `laundry room` (8), and `solar panels` (8). Two different issues dominate:

1. **Exact-label and specificity differences:** `walk-in closet` versus `walk in closet`, `car garage` versus `garage`, `private balcony` versus `balcony`, and `pools` versus `community pool` are not equated. A punctuation-only normalization sensitivity check changes the counts from 268 TP / 294 FP / 213 FN to 276 / 286 / 205 and F1 from 51.4% to 52.9%. This is illustrative only; no labels were changed and it does not address synonym or scope differences.
2. **Different annotation coverage:** the extractor emits many concrete mentions (`natural light`, `storage`, `flooring`, `dining area`) while human labels often select a different subset. Conversely, facilities such as `solar panels`, `ADU`, `pergola`, and `community pool` appear in Gold but are missed or represented by another phrase.

- **1179717732:** Gold includes `loft` and `workshop`, while the model misses these meaningful features; it also labels `doors` simply because Dutch doors are mentioned. The remarks describe a loft-style bedroom and sheds with workshop/studio use, so the Gold has listing-level feature decisions and the extractor has both an omission and an overly literal match.
- **1170100662:** The model finds `solar panels`, `garage`, `parking`, and other explicit features; Gold uses `garage` where the prediction says `attached garage`, and includes `ADU`/`pergola` where those are not in the extractor output. Gold omits some explicit details the model lists. This is partly granularity/coverage policy, partly missing taxonomy coverage.
- **1190824374:** Both sides identify the pool, spa, fitness center, and recreation room. The predicted `walk-in closet` differs from Gold's `walk in closet`; the model misses explicit `creek`, `laundry room`, and `stainless steel appliances`, while it emits narrower or inferred kitchen/appliance labels.

## Structured fields

The provided aggregate is 423/469 (90.2%). The following field accuracies and error counts follow the supplied holdout results: fireplace 34/50 (68.0%; 16 errors), view 32/45 (71.1%; 13 errors), bedrooms 33/39 (84.6%; 6 errors), and bathrooms 30/36 (83.3%; 6 errors). Unknown Gold values are excluded by the evaluator, so each denominator is smaller than 50 for view, bedrooms, and bathrooms.

### Fireplace: 16 disagreements

Fifteen rows are `pred=unknown`, `gold=false`; in each, `FireplaceYN` is blank and `FireplaceFeatures` is `None` (or null). Remarks often do not discuss a fireplace. The extractor does not use `FireplaceFeatures`, so it preserves unknown where Gold treats the structured sentinel as absence. Whether `None` is a reliable negative must be confirmed from the source schema; if it is, these are systematic extractor misses. If it means unavailable/unreported, these are Gold unknown-versus-false disagreements. The remaining row, **1190033644**, is `pred=true`, `gold=false` while source fields say `FireplaceYN=1` and `FireplaceFeatures=FamilyRoom,LivingRoom`; this is a direct conflict between Gold and structured source evidence, not a reasonable extractor false positive on the available record.

### View: 13 disagreements

Eleven rows are `pred=unknown`, `gold=false` with blank `ViewYN` and `View=None`; this has the same unknown-versus-negative sentinel issue as fireplace. **1190824374** is `pred=unknown`, `gold=true`: source view fields are blank/null, but Remarks say the living room overlooks “green woods and creek.” Gold may be using a reasonable textual inference (`overlooking`) that the current structured rule/keyword list does not cover. **1175801826** is `pred=true`, `gold=false`: the remarks explicitly say “garden views,” while the source `View` is `None`. This looks like a Gold inconsistency unless the annotation policy intentionally excludes garden views.

### Bedrooms: 6 disagreements

All six appear to be text parsing rather than missing database values: the relevant `L_Keyword2` source values are absent, while Remarks contain bedroom counts. Examples include **1190033644** (“three comfortable bedrooms,” Gold 3, prediction unknown), **1157651063** (“3-bedroom,” Gold 3, prediction unknown), **1172448599** (“1 Master Br,” Gold 1, prediction unknown), and **1183454528** (primary suite plus two additional bedrooms; Gold 3, prediction 2). Other errors include **1190459010** and **1179989786**, where the primary bedroom/suite must be counted along with secondary bedrooms. Hyphenated formats and abbreviations are likely parser gaps; counting suite plus “additional” bedrooms also requires careful aggregation.

### Bathrooms: 6 disagreements

Several Gold values are inferable by counting named fixtures/rooms, but are not stated as a total; those are annotation-standard questions rather than simple extraction failures. For instance, **1183454528** Gold says 2.5 based on primary/guest full baths plus a powder room, and **1190459010** Gold says 3.5 from described full and powder baths. **1157651063** explicitly says “2-bath,” and **1170100662** says “two recently refreshed bathrooms,” yet prediction is unknown in both cases; these are likely parser failures. **1191028821** and **1179989786** have Gold totals that appear to be derived by counting individual bath mentions, which needs a consistent policy for en-suites and shared baths.

## Development/holdout annotation consistency

The exact-match schema is sensitive to canonicalization differences already present across labels and prose. Examples include `townhouse` versus `townhome`, `condominium` versus `condo`, `walk in closet` versus `walk-in closet`, and `ocean view` versus `ocean views`. Gold and prediction also differ in specificity (`garage`/`attached garage`, `balcony`/`private balcony`, `pool`/`community pool`). The current evaluator lowercases and trims but does not normalize these forms, so semantically equivalent tags can be charged as one FP and one FN.

The holdout appears to use a different **coverage threshold** in several categories from the development set: holdout Gold has many fewer selected location phrases than the extractor emits and amenity Gold frequently selects a subset of explicit remarks. Development Gold's amenity score was much higher despite exact matching, while the holdout contains many spelling/specificity mismatches and more extensive omissions. This can reflect annotator selection policy, differences in listing text, or both; the CSV comparison alone cannot establish that one set of labels is wrong. Do not relabel solely to raise the score. Before future evaluation, define whether every supported mention should be labeled, how to handle nested phrases, secondary units, community facilities, and property-vs-room scope, then normalize both datasets under that policy.

## Root-cause assessment

| Root cause | Assessment |
|---|---|
| Exact-match evaluation / label normalization | High impact, especially amenities and location. Punctuation, singular/plural, and specificity variants create paired FP/FN counts. |
| Broad or overlapping taxonomy terms | High impact for location (`direct access`, broad destination words), condition (`maintained`, `custom`, `modern`), property type (`loft`, `studio`, `residence`), and amenities. |
| Context and scope | High impact for property type and location: room/ADU/shed descriptions are treated as listing-level type; direct access to an on-property feature is treated as location. |
| Missing phrase coverage / parser limits | Moderate to high impact: hyphenated `move-in ready`, `3-bedroom`, explicit bathroom counts, `overlooking` views, and specific amenity names. |
| Gold annotation consistency / evidence policy | Material, especially structured false versus unknown sentinels and which paraphrases/mentions merit a label. Some structured Gold values conflict with source data or prose. |
| Genuine extraction failures | Present, but the observed F1 gap cannot be attributed to extractor quality alone because exact-match and annotation-policy effects are substantial. |

## Recommended improvements, ranked by likely impact

1. **Set a shared annotation and scoring contract.** Specify canonical label vocabulary, whether nested labels are allowed, mention coverage, property/room/secondary-unit scope, community amenities, and how unknown differs from false. Apply it to any future independently labeled samples.
2. **Normalize labels before exact set scoring.** Use a versioned alias/canonicalization map for punctuation, singular/plural, and approved synonyms; preserve more-specific labels only when both sides intend that distinction. Report both raw exact and normalized results.
3. **Reduce context-blind taxonomy matches.** Require location context for destination words and exclude `direct access` when it refers to a door, patio, garage, or other on-property feature. Treat `loft`/`studio` as property type only when they describe the listing, not a room, shed, or possible ADU use.
4. **Improve phrase handling.** Normalize hyphens and common spelling variants before keyword matching; add evidence-backed aliases for phrases such as `fresh paint`/`freshly painted`, `move-in ready`, and `overlooking` view descriptions. Avoid emitting redundant nested labels unless the annotation contract requires them.
5. **Confirm source-field sentinel semantics.** Document whether `FireplaceFeatures=None` and `View=None` mean confirmed absence or missing data, then align extraction and Gold annotation policy. The current disagreement pattern is dominated by this distinction.
6. **Extend structured parsing with scoped counts.** Parse explicit bedroom/bathroom totals and common hyphenated/abbreviated forms, while avoiding double counting primary suites and separately described units. Keep inferred totals distinct from explicit totals for review.
7. **Use a separate untouched sample after any changes.** These 50 reviewed rows are diagnostic data; any changes motivated by them require evaluation on a new holdout before claims about generalization.

## Files and integrity

Only this report was created. The holdout and development CSVs, predictions, Gold Labels, `signal_extractor.py`, `evaluate_week6_gold.py`, and `taxonomy.json` were not modified.
