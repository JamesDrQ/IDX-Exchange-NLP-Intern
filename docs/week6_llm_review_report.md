# Week 6 Final Holdout: Second-Pass LLM Review

## Review summary

- **Listings reviewed:** 100 of 100. I read each complete Remarks field and its `source_fields_json`; one listing, `1179064657`, has empty Remarks.
- **Gold fields populated:** 1,700 of 1,700 (17 per listing).
- **Gold fields corrected:** 76 cells changed relative to the CSV before this second pass. These cells contain 104 scalar or set-label additions/removals when the changed array contents are counted individually.
- **AI review status:** `llm_review_status=reviewed` on all 100 rows.
- **Existing `review_status`:** Preserved as `done` on every row because those were the pre-review values. This second-pass AI review did not set or change them.
- **Predictions/source data:** Listing IDs, order, complete Remarks, `source_fields_json`, and every `pred_*` value were verified unchanged against the pre-review backup. Predictions were not consulted to make annotation decisions.
- **Evaluation:** Not run; no performance metrics were calculated.

The pre-review backup is `data/processed/week6_final_holdout_review_pre_llm_backup.csv`.

## Representative corrections

| Listing ID | Gold field | Correction and evidence |
| --- | --- | --- |
| `1089995500` | City; bathrooms; financial | Changed city from unknown to `Glyfada`, which is explicitly named in Remarks. Changed bathrooms from 3.5 to unknown because “one more bathroom, and a WC” does not establish how many bathrooms belong to the two master bedrooms. Removed `investment`: the listing describes a golf-area apartment but makes no investment claim. |
| `1152543533` | Bedrooms; bathrooms | Changed both from unknown to 4 and 3. The remarks explicitly say the “Family Lodge has 4 Bedrooms, 3 Bathrooms.” Acreage remains excluded from living area. |
| `1191039468` | Financial | Added `investment opportunity`: Remarks describe potential for homeowners and investors and an investor seeking a value-add property. |
| `1188130807` | Financial | Removed `rental income`; it is explicitly only potential income while the buyer considers unapproved conceptual development plans. Kept the stated investment opportunity. |
| `1190314023` | Condition; location | Replaced broad `updated` with the more specific `beautifully updated` wording and added `shopping and dining`, which is explicitly paired with easy access. |
| `1172990701` | Pool flags; condition; amenities | Changed private/community pool flags from unsupported true/false assignments to unknown: the source says `InGround` but supplies no ownership type. Removed `newer`, which referred to the roof, removed an unsupported patio, and replaced generic `center island` with the described island. |
| `1177996070` | Condition; financial; amenities | Removed `custom` (custom stonework is not a custom overall dwelling label), `newer` (roof only), potential `rental income`, a nonexistent fire pit, and an overly specific smart-home hub tag. Used the more specific `private pool` label for the explicitly private pool. |
| `1175214840` | Amenities | Removed `playground`: the children’s playground is described as nearby, not as a property or included association amenity. |
| `1190868670` | Financial | Removed `investment opportunity`; the remarks describe an opportunity for first-time buyers and low-maintenance living, not an investment claim. |
| `1189560705` | Condition; amenities | Removed `newer` because it describes the ADU rather than the primary dwelling; removed `updated kitchen` and duplicate generic `windows`, which are not supported as written. |
| `1189429592` | Private-pool flag; view tags | Changed private pool from true to unknown because `PoolPrivateYN=1` conflicts with community-only `PoolFeatures` and community-pool remarks. Removed `panoramic views`, which appears in source fields but not Remarks. |
| `1190317005` | Financial; amenities | Removed `price reduction`, which is absent from the remarks, and used `private pool` for the explicitly private backyard swim system. |

## Label consistency findings

- Reapplied the guideline that a known pool type does not make the other type false. A private pool without community-pool evidence now has `community_pool=unknown`; community-only pool evidence leaves `private_pool=unknown`. `PoolFeatures="None"` remains the no-pool sentinel unless other evidence confirms a pool.
- Kept `private_pool` and `community_pool` true independently when both are supported. For example, the private pool and separate community pools at `1182480319` are both described.
- Removed potential income as confirmed `rental income`; retained explicit investment-opportunity language where the remarks support it.
- Removed labels for public/nearby facilities, future uses, and component-only condition claims where they had been treated as existing property amenities or whole-home condition.
- Removed duplicate broad labels when a more specific supported label describes the same feature, and normalized the confirmed synonyms to the guideline vocabulary.

## Unresolved cases for human attention

These are evidence or interpretation limits, not reasons to guess:

- **`1089995500`:** City is explicit, but total bathrooms remain unknown because the master-suite bathroom configuration is unstated. Pool fields say `SeeRemarks` without pool details.
- **`1191009008`, `1183993128`, `1189560705`:** Multi-unit/ADU count scope differs from the main residence; the holdout schema does not define whether listing-wide counts should include every unit. The labels use the explicit main-dwelling counts where available, or unknown when totals are unclear.
- **`1177996070`, `1174221287`, `1191032026`:** A media/den/loft or model-plan room could become another bedroom, but is not counted as a current bedroom without explicit current-use evidence.
- **`1159456015`, `1181369338`, `1175356448`:** Bedroom suites and an attached casita create bathroom-count or count-scope ambiguity; recheck against the rubric’s treatment of accessory suites.
- **`1189429592`, `1176374768`, `1189347125`:** `PoolPrivateYN=1` conflicts with community-only pool features or Remarks. Private pool is left unknown pending source-schema clarification; community pool is supported.
- **`1190152445`:** `PoolFeatures` contains both `None` and `Association`; the remarks clearly confirm a community pool, so pool/community are true and private status remains unknown. The mixed source token should be checked.
- **`1172990701`, `1182414634`:** Pool presence is confirmed, but `InGround` alone does not distinguish private from community ownership. The corresponding type flags remain unknown unless a reliable private indicator is present.
- **`1177240889`, `1179300604`, `1191032026`:** New-build or rendering language includes future completion, buyer options, or lease/purchase choices. Existing-facility and completed-condition labels should be reviewed against the project’s timing convention.
- **`1191002446`:** The remarks identify a 50-amp EV outlet, but do not establish that a charging unit is installed; no `private ev charger` amenity is assigned.
- **`1179064657`:** Remarks are empty. Structured price, city, pool sentinel, fireplace and view values are available, but no text tags can be annotated.
- **`1183447590`:** The dock, pier, and boat lift exist but are described as needing repair/restoration; they were omitted as usable amenities.

## Validation

The final CSV has 100 unique listings in the original order, 17 complete Gold fields per row, valid numeric/city and three-valued flag cells, and valid JSON arrays of strings for every keyword and amenity field. All `llm_review_status` values are `reviewed`. Source fields, Remarks, prediction cells, and the pre-existing `review_status` values match the pre-review copy.

## Limitations

This is a second-pass LLM annotation review, not independent human verification. Listing prose can be promotional, structured fields can conflict, and several schema rules—especially unit-wide counts, pool ownership, and incomplete construction—need a project-owner decision. No accuracy, precision, recall, or F1 result is claimed. The existing `review_status=done` values were preserved as requested; they should be interpreted according to the pre-review workflow and not as evidence that this LLM pass was human verified.
