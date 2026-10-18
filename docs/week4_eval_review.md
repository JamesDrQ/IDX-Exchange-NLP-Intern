# Week 4 Query Evaluation Review

Review the expected filters below before using this dataset as evaluation ground truth. The Review Status column is intentionally blank for manual review.

| # | ID | Natural-language query | Expected PropertyFilters | Review Status |
|---:|:---|:---|:---|:---|
| 1 | q01 | Find homes under $700k | `{price_max=700000}` |  |
| 2 | q02 | Show properties below $1.2m | `{price_max=1200000}` |  |
| 3 | q03 | I'm looking for a condo costing less than $800,000 | `{price_max=800000}` |  |
| 4 | q04 | Homes over $500k, please | `{price_min=500000}` |  |
| 5 | q05 | My budget is above $600k | `{price_min=600000}` |  |
| 6 | q06 | Properties priced between $500k and $900k | `{price_min=500000, price_max=900000}` |  |
| 7 | q07 | Looking for a home with 3 bedrooms | `{bedrooms_min=3, bedrooms_max=3}` |  |
| 8 | q08 | Need a 3 bed house | `{bedrooms_min=3, bedrooms_max=3}` |  |
| 9 | q09 | At least 3 bedrooms | `{bedrooms_min=3}` |  |
| 10 | q10 | Minimum 3 beds, if possible | `{bedrooms_min=3}` |  |
| 11 | q11 | 3+ bedrooms would be ideal | `{bedrooms_min=3}` |  |
| 12 | q12 | Up to 4 bedrooms | `{bedrooms_max=4}` |  |
| 13 | q13 | No more than 4 beds | `{bedrooms_max=4}` |  |
| 14 | q14 | Between 2 and 4 bedrooms | `{bedrooms_min=2, bedrooms_max=4}` |  |
| 15 | q15 | 2 bathrooms | `{bathrooms_min=2.0, bathrooms_max=2.0}` |  |
| 16 | q16 | A place with 2.5 baths | `{bathrooms_min=2.5, bathrooms_max=2.5}` |  |
| 17 | q17 | 2+ bathrooms preferred | `{bathrooms_min=2.0}` |  |
| 18 | q18 | At least 2 baths | `{bathrooms_min=2.0}` |  |
| 19 | q19 | Minimum 1.5 bathrooms, please | `{bathrooms_min=1.5}` |  |
| 20 | q20 | Up to 3 bathrooms is fine | `{bathrooms_max=3.0}` |  |
| 21 | q21 | No more than 2.5 baths | `{bathrooms_max=2.5}` |  |
| 22 | q22 | Between 2 and 3.5 bathrooms | `{bathrooms_min=2.0, bathrooms_max=3.5}` |  |
| 23 | q23 | Show me homes in Irvine | `{city="Irvine"}` |  |
| 24 | q24 | Properties in San Diego, please | `{city="San Diego"}` |  |
| 25 | q25 | Looking for a condo in Los Angeles | `{city="Los Angeles"}` |  |
| 26 | q26 | Sacramento homes, please | `{city="Sacramento"}` |  |
| 27 | q27 | Are there properties in Anaheim? | `{city="Anaheim"}` |  |
| 28 | q28 | I'd like listings around Oakland | `{city="Oakland"}` |  |
| 29 | q29 | Fremont homes near good schools | `{city="Fremont"}` |  |
| 30 | q30 | With a pool | `{pool=True}` |  |
| 31 | q31 | The home has a private pool | `{pool=True}` |  |
| 32 | q32 | Homes with swimming pools are preferred | `{pool=True}` |  |
| 33 | q33 | Pool required | `{pool=True}` |  |
| 34 | q34 | Without a pool | `{pool=False}` |  |
| 35 | q35 | No swimming pool | `{pool=False}` |  |
| 36 | q36 | I don't want a pool | `{pool=False}` |  |
| 37 | q37 | Looking for homes without private pools | `{pool=False}` |  |
| 38 | q38 | Find 3+ bedroom homes in Irvine under $1.2m with a pool | `{city="Irvine", price_max=1200000, bedrooms_min=3, pool=True}` |  |
| 39 | q39 | San Diego houses with at least 2 bedrooms and 2.5 baths below $900,000 | `{city="San Diego", price_max=900000, bedrooms_min=2, bathrooms_min=2.5, bathrooms_max=2.5}` |  |
| 40 | q40 | No more than 4 beds in Sacramento, between $450k and $750k, and no swimming pool | `{city="Sacramento", price_min=450000, price_max=750000, bedrooms_max=4, pool=False}` |  |
| 41 | q41 | Los Angeles condos with 2 bathrooms, a private pool, and a price above $600k | `{city="Los Angeles", price_min=600000, bathrooms_min=2.0, bathrooms_max=2.0, pool=True}` |  |
| 42 | q42 | Find 3 bed, 2 bath homes in Berkeley under $800k | `{city="Berkeley", price_max=800000, bedrooms_min=3, bedrooms_max=3, bathrooms_min=2.0, bathrooms_max=2.0}` |  |
| 43 | q43 | Pasadena homes with 2+ beds, at least 1.5 bathrooms, pool required, and above $500k | `{city="Pasadena", price_min=500000, bedrooms_min=2, bathrooms_min=1.5, pool=True}` |  |
| 44 | q44 | Homes in San Jose with 2+ baths and at least 2 bedrooms | `{city="San Jose", bedrooms_min=2, bathrooms_min=2.0}` |  |
| 45 | q45 | Riverside 4 bedrooms under $700k without a pool | `{city="Riverside", price_max=700000, bedrooms_min=4, bedrooms_max=4, pool=False}` |  |
| 46 | q46 | No more than 3 beds and up to 2.5 baths in Santa Ana between $500k and $900k | `{city="Santa Ana", price_min=500000, price_max=900000, bedrooms_max=3, bathrooms_max=2.5}` |  |
| 47 | q47 | Find a Sunnyvale home with minimum 3 beds, 2+ baths, and a pool, below $1.5m | `{city="Sunnyvale", price_max=1500000, bedrooms_min=3, bathrooms_min=2.0, pool=True}` |  |
| 48 | q48 | I have two kids and would like to see some houses next month | `{}` |  |
| 49 | q49 | I'm comparing neighborhoods and just browsing for now | `{}` |  |
| 50 | q50 | Show me a few homes when you have a chance | `{}` |  |
