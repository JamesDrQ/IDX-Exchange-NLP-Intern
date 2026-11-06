# Week 6 Gold Annotation Guidelines

## Purpose and scope

These rules define a consistent evidence standard for the Week 6 Gold Review schema. Annotate what the listing Remarks state, using `source_fields_json` for structured facts and to distinguish property, association, and nearby facilities. The Gold labels describe listing evidence; they are not required to agree with extractor output. Do not consult `pred_*` values while deciding labels.

Use the exact canonical spellings in the inventories below. Apply the alias rules in this document before saving labels. The evaluator compares tags as exact, case-insensitive strings; it does not infer synonym equivalence.

## Canonical keyword labels

The following are the canonical taxonomy labels for each keyword field. Extra phrase labels already implemented by the extractor are separately identified after the taxonomy inventory.

### `condition`

`updated`, `modern`, `custom`, `remodeled`, `upgraded`, `luxury`, `maintained`, `newer`, `renovated`, `turnkey`, `beautifully maintained`, `beautifully updated`, `beautifully remodeled`, `new flooring`, `brand new`, `move in ready`, `recently renovated`, `recently remodeled`, `well maintained`, `freshly painted`

### `financial`

`hoa`, `income`, `rental`, `investment`, `rental income`, `low hoa`, `no hoa`, `hoa fees`, `price reduction`, `investment opportunity`, `rental property`, `income property`, `property taxes`, `monthly hoa`, `assumable loan`, `cash flow`, `lease income`, `seller financing`, `closing costs`, `price improvement`

### `location`

`schools`, `beach`, `parks`, `restaurants`, `downtown`, `nearby`, `freeway`, `freeways`, `conveniently located`, `minutes from`, `just minutes`, `located near`, `easy access`, `close to`, `ideally located`, `direct access`, `convenient access`, `walking distance`, `school district`, `near shopping`, `close to shopping`, `access to shopping`, `shopping and dining`, `unified school district`, `near the beach`

### `property_type`

`residence`, `condo`, `loft`, `studio`, `condominium`, `townhouse`, `townhome`, `single family home`, `single family residence`, `duplex`, `triplex`, `fourplex`, `bungalow`, `cottage`, `villa`, `apartment`, `manufactured home`, `mobile home`, `multi family home`, `penthouse`

### `view`

`views`, `view`, `panoramic`, `mountain views`, `ocean views`, `city view`, `city views`, `water view`, `water views`, `golf course view`, `pool view`, `park view`, `mountain view`, `ocean view`, `panoramic views`

### `amenities`

For amenity labels, use only the active feature inventory supported by `EntityExtractor`: taxonomy terms in `amenity`, `interior_feature`, `exterior_feature`, and `view` after its generic-term exclusions, plus the existing Week 3/Week 6 development terms listed below. Choose the most specific applicable term when the remarks name it (for example, `mature landscaping` rather than both it and `landscaping`). Do not create new labels to resemble predictions.

`smart home automation technology hub`, `granite art corner display shelves`, `assigned covered parking space`, `panoramic pauma valley views`, `2 car direct access garage`, `covered entertaining areas`, `stainless steel appliances`, `detached finished garage`, `luxurious primary suite`, `sparkling swimming pool`, `vaulted beamed ceilings`, `assigned 2 car parking`, `dedicated laundry room`, `outdoor storage room`, `vinyl plank flooring`, `frosted back panels`, `granite countertops`, `wood-style flooring`, `built-in microwave`, `formal dining room`, `mature landscaping`, `private ev charger`, `quartz countertops`, `standing wardrobes`, `dual-pane windows`, `first floor suite`, `pickleball courts`, `quartz countertop`, `recessed lighting`, `remodeled kitchen`, `resort style pool`, `separate entrance`, `spacious bedrooms`, `24-hour security`, `city-scape views`, `community center`, `custom cabinetry`, `golf course view`, `newer front door`, `primary bathroom`, `private backyard`, `private driveway`, `soaring ceilings`, `vaulted ceilings`, `washer and dryer`, `18+ ft ceilings`, `artificial turf`, `attached garage`, `bonus loft area`, `california room`, `detached garage`, `finished garage`, `gardening space`, `gated community`, `gourmet kitchen`, `hardwood floors`, `new hvac system`, `outdoor kitchen`, `panoramic views`, `primary bedroom`, `primary retreat`, `private balcony`, `recreation room`, `stone fireplace`, `updated kitchen`, `walk-in closets`, `bedroom/office`, `community pool`, `fitness center`, `full bathrooms`, `hillside views`, `indoor laundry`, `interior doors`, `mountain views`, `screened patio`, `sparkling pool`, `stone flooring`, `two-car garage`, `walk in closet`, `walk-in closet`, `walk-in pantry`, `walk-in shower`, `walking trails`, `breakfast bar`, `center island`, `community spa`, `covered patio`, `covered porch`, `dual vanities`, `full bathroom`, `guest parking`, `high ceilings`, `large windows`, `mountain view`, `natural light`, `newer windows`, `outdoor grill`, `primary suite`, `privacy fence`, `private patio`, `secure garage`, `tennis courts`, `tile flooring`, `1 car garage`, `6 person spa`, `ceiling fans`, `chef kitchen`, `covered deck`, `ensuite bath`, `french doors`, `garden level`, `laundry room`, `new flooring`, `paver patios`, `private pool`, `refrigerator`, `rooftop pool`, `rose gardens`, `solar panels`, `sports court`, `dining area`, `dining room`, `family room`, `fenced yard`, `glass doors`, `golf course`, `home office`, `landscaping`, `living room`, `ocean views`, `soaking tub`, `water views`, `appliances`, `bonus room`, `car garage`, `city views`, `dishwasher`, `front yard`, `great room`, `guard gate`, `jetted tub`, `large shed`, `newer roof`, `ocean view`, `playground`, `water view`, `back yard`, `cabinetry`, `city view`, `clubhouse`, `courtyard`, `fireplace`, `gas stove`, `park view`, `pool view`, `promenade`, `side yard`, `backyard`, `bbq area`, `dog park`, `driveway`, `elevator`, `fire pit`, `flooring`, `grilling`, `lighting`, `new roof`, `pavilion`, `security`, `balcony`, `cabanas`, `carport`, `ensuite`, `kitchen`, `parking`, `storage`, `terrace`, `windows`, `carpet`, `closet`, `garage`, `garden`, `island`, `pantry`, `shower`, `doors`, `patio`, `porch`, `deck`, `pool`, `roof`, `spas`, `yard`, `gym`, `spa`

### Existing supplemental keyword labels

The current `SignalExtractor` also defines these labels outside `taxonomy.json`. They are allowed only when their exact evidence pattern is present:

- `condition`: `needs_repairs`, `fixer_upper`
- `financial`: `seller_financing_possible`, `seller_financing_available`
- `location`: `near_lake`

## Synonym and canonicalization rules

- Ignore capitalization, repeated whitespace, and ordinary hyphenation when identifying a phrase. Save only the canonical label spelling shown above.
- Normalize `walk-in closet` / `walk in closets` to `walk in closet`; `walk-in shower` to `walk in shower`; and `walk-in pantry` to `walk in pantry`.
- Normalize `townhouse` to `townhome`, `condominium` to `condo`, and `single family residence` to `single family home`.
- Normalize `just minutes from` to `minutes from`. Do not emit both for one proximity phrase.
- Normalize explicit `fresh paint` / `freshly painted` statements to `freshly painted`.
- When a specific and broad term describe the same single feature, use only the most specific supported label. Preserve separate labels when the text describes distinct facts (for example, a home has a `rental property` and separately notes `property taxes`). Do not collapse meaningful distinctions such as `private balcony` versus `balcony`, `community pool` versus `private pool`, or `ocean views` versus `mountain views`.
- Do not infer a synonym when the evidence only loosely suggests it. If no canonical label fits, omit the keyword rather than inventing one; explain recurring out-of-vocabulary concepts in reviewer notes/report.

## Keyword category rules

### Condition

Label the condition or readiness of the dwelling itself: e.g. `updated`, `remodeled`, `renovated`, `turnkey`, `move in ready`, `brand new`, `newer`, `freshly painted`, or `needs_repairs`. Use `custom`, `modern`, `luxury`, `upgraded`, or `maintained` only when the statement describes the home’s overall condition/finish. Do not label `custom` from “custom cabinetry,” `luxury` from “luxury appliances,” or a renovation/maintenance claim about only the HOA, common area, landscaping, or neighboring property. For `recently renovated`, label only when the property itself is the subject. Do not infer `brand new` from a new roof or new appliance.

### Financial

Label explicit sale, ownership-cost, investment, rental, or financing language. Prefer the most specific label for one phrase: “rental income” is `rental income`, not separate `rental` and `income`; “price improvement” is `price improvement`, not automatically `price reduction`. A routine HOA/community mention is not itself an HOA fee claim; use `hoa`, `hoa fees`, `monthly hoa`, `low hoa`, or `no hoa` only when the Remarks support that meaning. A potential or hoped-for income source is not confirmed income; use investment/opportunity language only when explicitly stated.

### Location

Label stated proximity/access to destinations, not just any mention of a destination. Use taxonomy terms such as `near shopping`, `walking distance`, `near the beach`, `freeways`, `schools`, or `parks` when the Remarks make a nearby/location relation clear. Nearby public facilities are location signals, not property amenities. A facility mentioned as part of a property’s grounds or included association amenity belongs in `amenities`, not automatically in `location`. “Direct access” to a patio, garage, carport, or room is not a location label. For “near a park,” use the canonical `parks` label if the location claim is clear; do not invent `near a park`.

### Property type

Label the type of the listing’s primary dwelling only, using an explicit description such as `cottage`, `townhome`, `condo`, `single family home`, `manufactured home`, `duplex`, or `studio`. A room, floor, or possible use does not define the property type. An upstairs/bonus loft is not a `loft` property type; a shed or ADU described as a possible studio/workspace is not a studio property. If the listing combines a main home and an accessory unit and the overall type or counts are unclear, annotate only the explicit primary type and leave unsupported values unknown.

### View

Label a view only when Remarks describe what the property looks out onto (e.g. mountain, ocean, city, water, golf course, park, panoramic). Use the most specific supported taxonomy term. Generic `view` / `views` is appropriate only when a view is explicit but the object is unspecified. A park, beach, or mountain mentioned as nearby is not automatically a view. “Overlooking” an object is direct view evidence. Do not convert scenery or neighborhood proximity into a view without explicit visual relation.

### Amenities

Label a feature or facility that belongs to the property or is an included community/association amenity. Use the taxonomy feature label that best matches the explicit phrase; include an association pool, gym, clubhouse, or recreation area when it is an amenity available to residents. Do not label nearby public parks, public beaches, restaurants, schools, or unrelated golf facilities as property amenities. Do not convert aspirational phrases (“room for,” “could add,” “potential for”) into existing features. A planned/in-progress feature is not an existing amenity unless the Remarks confirm it is installed and usable.

For the named examples:

- `mature landscaping`: use this exact amenity label when mature landscaping is on the property. If the words describe a nearby community or general neighborhood, do not label it as a property amenity.
- `upstairs loft`: use an appropriate loft-area amenity label only when it is an existing usable part of the home; never use property-type `loft` solely because an upstairs room is a loft. If the text only says “loft-style bedroom,” do not infer an additional loft room.
- `near a park`: location label `parks` when proximity is clear; not an amenity.
- `recently renovated`: condition label only if it refers to the dwelling. If it refers to common-area balconies or landscaping, do not label the home’s condition.

## Negation, proposals, optional facilities, and uncertainty

- Respect explicit negatives: “no pool,” “without a garage,” “not renovated,” and “no HOA” must not create a positive mention of the negated signal. A negative amenity does not create a keyword tag unless a supported category label itself describes the negative claim.
- A proposal, plan, possibility, or future improvement is not an existing amenity or completed condition: “could add a pool,” “planned playground,” and “room for an ADU” are not positive facility/type labels.
- A separate-fee club, optional membership, or facility outside the property/association is not a property/community amenity. If the Remarks clearly say residents have access through an optional paid membership, record the facility only when the project’s association/community definition includes it; otherwise flag the row for review rather than guessing.
- Use `unknown` for scalar facts when evidence is missing, ambiguous, contradictory, or cannot distinguish the primary home from an accessory unit. Missing information is never automatically `false`.
- Use `[]` for keyword/amenity arrays only when no applicable positive text label is supported. An explicit denial does not become a positive tag. Arrays must be valid JSON arrays of strings.

## Structured fields and three-valued flags

### Numeric and city entities

- `price`: prefer positive `L_SystemPrice`; use an explicit listing price in Remarks only when the structured value is absent/unusable. Do not use HOA fees, discounts, income, lot price, or financing amounts as the sale price.
- `city`: use `L_City` when present. Do not replace it with a nearby city or neighborhood.
- `bedrooms`: use an explicit total for the primary dwelling. Count rooms only when the Remarks unambiguously enumerate the full primary-dwelling count. Do not add a separate ADU’s bedrooms unless the source establishes the requested total includes it; otherwise `unknown`.
- `bathrooms`: use an explicit total. Sum described full/half baths only if the list is complete and unambiguous. Do not count a powder room as a full bath or double-count a suite bath. Separate-unit totals that cannot be resolved are `unknown`.
- `sqft`: use living/building area, not lot acreage/square footage, garage size, or a combined multi-unit area whose scope is unclear. Use `unknown` if only land size or an ambiguous total is stated.

### Boolean flags

Each flag is `true`, `false`, or `unknown`:

- `pool`: any existing pool associated with the property or its resident community.
- `private_pool`: an existing private pool belonging to the listed property.
- `community_pool`: an existing shared/association pool for residents.
- `garage`, `fireplace`, `view`: the relevant existing property feature/view.

Use reliable structured booleans (`PoolPrivateYN`, `GarageYN`, `FireplaceYN`, `ViewYN`) as primary evidence. `PoolPrivateYN=0` establishes no private pool but does not establish no community pool. `PoolFeatures` with `Community` or `Association` supports `community_pool=true`; a private token supports `private_pool=true`. `PoolFeatures="None"` is the project’s explicit no-pool sentinel and supports `pool=false`, `private_pool=false`, and `community_pool=false` unless Remarks or another structured field affirm an existing pool. Blank pool fields mean `unknown`. If database and text conflict, use `unknown` and document the conflict rather than choosing silently.

For fireplace, `FireplaceYN=1/0` establishes true/false; feature names support true when the boolean is absent. `FireplaceFeatures="None"` with no boolean or Remarks evidence remains `unknown` unless the source schema confirms it is a negative sentinel. For view, `ViewYN=1/0` establishes true/false; a populated non-sentinel `View` value supports true, while blank/`None` alone is not a negative. Explicit Remarks evidence can support a true flag. A flag is false only with reliable explicit negative evidence; otherwise it remains unknown.

A structured contradiction (for example, boolean zero but explicit text says the facility exists) should be noted for human review and labeled `unknown` unless one source is clearly authoritative under these rules.

## Review and evidence notes

The final holdout remains an independent test set. Do not revise this policy based on predictions or observed holdout metrics. Keep `review_status=pending` until a human reviewer verifies each row. Record uncertainty/conflicts in `reviewer_notes`; do not resolve them by guessing.
