# Week 7 — Query Intent Labeling Guidelines

## Objective
Classify real estate search queries based only on their language.
Do not use behavioral data, CRM data, or assumed buyer identity.

## Intent Categories

### browsing
General property exploration without clear comparison or
immediate action.

Examples:
- Show me homes in San Diego
- Find 3 bedroom condos in Irvine
- Homes under 900k

### researching
Queries focused on evaluation, comparison, affordability,
neighborhood characteristics, taxes, or HOA costs.

Examples:
- Compare condos with low HOA fees
- Which neighborhoods have lower property taxes?
- Best areas for investment properties

### high_intent_inquiry
Queries suggesting near-term viewing, contacting an agent,
checking availability, or preparing for a transaction.

Examples:
- Schedule a home tour tomorrow
- Are there open houses this weekend?
- I want to contact the listing agent today
- Move-in ready homes under 1.2m in San Diego

## Annotation Rules

1. Use only the query text.
2. Specific price, bedroom, or location filters alone
   do not indicate high intent.
3. Favor researching when the user is evaluating options.
4. Favor high_intent_inquiry when there is a clear
   near-term action or transaction-related request.
5. Do not automatically map Week 4 intent labels
   to Week 7 labels.
6. Review ambiguous queries individually.
7. Keep labels consistent across similar queries.

## Limitations

Language-based intent does not establish actual buyer readiness.
Some queries may reasonably fit multiple categories.
Model confidence is not guaranteed to be calibrated.
