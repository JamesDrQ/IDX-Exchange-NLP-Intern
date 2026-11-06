"""Week 6: listing-level structured signal extraction.

Usage (from project root):
    from scripts.signal_extractor import SignalExtractor
    result = SignalExtractor().extract_signals(listing_dict)

This module is deliberately inference-only: it does not connect to MySQL or write files.
"""

import json
import re
from pathlib import Path

from scripts.entity_extractor import EntityExtractor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = PROJECT_ROOT / "data" / "processed" / "taxonomy.json"
KEYWORD_CATEGORIES = ("condition", "financial", "location", "property_type", "view")
MISSING_VALUES = {"", "none", "null", "n/a", "na", "unknown", "not specified", "no", "n", "0", "false"}


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def _term_pattern(term):
    """Match taxonomy phrases across ordinary spacing/hyphen variants."""
    pieces = re.split(r"\s+", term.strip())
    body = r"[\s\u2010-\u2015-]+".join(re.escape(piece) for piece in pieces if piece)
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.I)


def _canonical_keyword(category, term):
    """Map surface variants to the stable labels used by the Week 6 schema."""
    label = re.sub(r"\s+", " ", term.casefold().strip())
    aliases = {
        "condition": {
            "beautifully remodeled": "remodeled",
            "recently remodeled": "remodeled",
            "recently renovated": "renovated",
            "beautifully updated": "updated",
            "fresh paint": "freshly painted",
        },
        "location": {
            "just minutes": "minutes from",
        },
    }
    return aliases.get(category, {}).get(label, label)


def _canonical_amenity(term):
    raw = re.sub(r"\s+", " ", term.casefold().strip())
    normalized = re.sub(r"[-\u2010-\u2015]+", " ", raw.replace("\u2011", "-"))
    normalized = re.sub(r"\s+", " ", normalized)
    aliases = {
        "walk in closet": "walk in closet",
        "walk in closets": "walk in closet",
        "walk in shower": "walk in shower",
        "walk in pantry": "walk in pantry",
        "stainless steel appliances": "stainless steel appliances",
    }
    return aliases.get(normalized, raw)


def _contextually_valid(category, term, text, start, end):
    """Reject high-risk literal matches whose local context changes the label."""
    before = text[max(0, start - 90):start]
    after = text[end:min(len(text), end + 90)]
    clause_before = re.split(r"[.!?;\n]", before)[-1]
    clause_after = re.split(r"[.!?;\n]", after)[0]
    low_term = term.casefold()

    if category == "condition":
        if re.search(r"\b(?:hoa|homeowners association|community)\b", clause_before, re.I) and re.search(
            r"\b(?:balcon(?:y|ies)|landscaping|reserves?|amenities)\b", clause_after, re.I
        ):
            return False
        if re.search(r"\b(?:hoa|homeowners association|community)\b", clause_after, re.I) and re.search(
            r"\b(?:well|beautifully|recently)\s+\w+ed\b", clause_before, re.I
        ):
            return False
        # A condition label should describe the dwelling, not an HOA or a
        # separately mentioned feature/community.
        if low_term in {"maintained", "well maintained", "beautifully maintained"} and re.search(
            r"\b(?:hoa|association|community|balcon(?:y|ies)|landscaping|reserves?)\b",
            clause_before, re.I,
        ):
            return False
        if low_term == "custom" and re.match(
            r"\s+(?:cabinetry|cabinets?|countertops?|woodwork|built-ins?)\b", after, re.I
        ):
            return False
        if low_term == "luxury" and re.match(
            r"\s+(?:appliances?|amenities|fixtures|finishes)\b", after, re.I
        ):
            return False

    if category == "location":
        if low_term == "direct access":
            if re.search(
                r"\b(?:to\s+)?(?:the\s+)?(?:covered\s+|shaded\s+|front\s+|rear\s+)?"
                r"(?:patio|carport|garage|door|backyard|yard|home|unit)\b",
                after[:60], re.I,
            ):
                return False
        if low_term == "beach" and re.match(r"\s*[- ](?:inspired|style|themed)\b", after, re.I):
            return False

    if category == "property_type":
        if low_term == "loft" and re.match(
            r"\s*[- ]?style\s+(?:bedroom|space|area)\b|\s+(?:bedroom|space|area|sheds?)\b",
            after, re.I,
        ):
            return False
        if low_term == "studio" and (
            re.search(r"\b(?:studio)\s+(?:layout|workspace|work\s+space|option|use)\b", clause_after, re.I)
            or re.search(r"\b(?:shed|adu|office|workshop|storage)\b", clause_before, re.I)
        ):
            return False

    return True


def _available(value):
    return value is not None and str(value).strip().casefold() not in MISSING_VALUES


def _boolean(value):
    """Parse database boolean formats; None means unknown, not False."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    return None


def _negated(text, start, end):
    """Conservative local negation guard for keyword/feature matches."""
    before = text[max(0, start - 60):start].split(".")[-1].split(";")[-1]
    after = text[end:end + 28]
    prefix = (
        r"\b(?:no|without|lacks?|not|never)\s+"
        r"(?:(?:a|an|any|private|shared|community|the|on-site)\s+){0,3}$"
    )
    suffix = r"^\s+(?:(?:is|are|was|were)\s+)?(?:not\s+available|not\s+included|excluded)\b"
    coordinated = (
        r"\b(?:no|without)\s+(?:a\s+|any\s+)?"
        r"[\w-]+\s+(?:or|and)\s+$"
    )
    return bool(
        re.search(prefix, before, re.I)
        or re.search(coordinated, before, re.I)
        or re.search(suffix, after, re.I)
    )


def _feature_signal(text, pattern):
    """Return True for positive mention, False for explicit denial, else None."""
    matches = list(re.finditer(pattern, text, re.I))
    if any(not _negated(text, m.start(), m.end()) for m in matches):
        return True
    if matches:
        return False
    return None


def _pool_text_signal(text, pattern):
    """Find current pool claims, excluding negated, hypothetical, or optional mentions."""
    matches = list(re.finditer(pattern, text, re.I))
    positive = False
    denied = False
    for match in matches:
        if _negated(text, match.start(), match.end()):
            denied = True
            continue
        # Use the current sentence so a nearby proposal does not taint other
        # affirmative pool descriptions in the remarks.
        start = max(text.rfind(mark, 0, match.start()) for mark in (".", "!", "?", ";")) + 1
        clause = text[start:match.start()]
        after = text[match.end():match.end() + 100]
        proposed = re.search(
            r"\b(?:potential|possibility|opportunity|imagine|picture|envision|"
            r"could|may|might|planned|proposed)\b.{0,100}$",
            clause, re.I,
        ) or re.search(r"\b(?:room|space)\s+to\s+(?:add|build|install|create)\b", clause, re.I)
        optional = (
            re.search(r"\bseparate\s+fee\b", clause, re.I)
            and re.search(r"\b(?:membership|join|access)\b", clause, re.I)
        ) or re.search(r"\bmembership\s+(?:is\s+)?required\b", after, re.I)
        if proposed or optional:
            continue
        positive = True
    if positive:
        return True
    if denied:
        return False
    return None


def _pool_feature_tokens(value):
    """Normalize the comma-separated RETS PoolFeatures enumeration."""
    if not isinstance(value, str) or not value.strip():
        return set()
    return {part.strip().casefold() for part in value.split(",") if part.strip()}


class SignalExtractor:
    def __init__(self, taxonomy_path=None, entity_extractor=None):
        path = Path(taxonomy_path) if taxonomy_path else TAXONOMY_PATH
        with path.open("r", encoding="utf-8") as handle:
            taxonomy = json.load(handle)

        self.entity_extractor = entity_extractor or EntityExtractor()
        terms_by_category = {category: set() for category in KEYWORD_CATEGORIES}
        for item in taxonomy["terms"]:
            category = item.get("category")
            term = item.get("term", "").strip()
            if category in terms_by_category and len(term) >= 3:
                terms_by_category[category].add(term)

        # Compile once, rather than once per row for all 55K listings.
        self.patterns = {
            category: [
                (term, _term_pattern(term))
                for term in sorted(terms, key=lambda t: (-len(t), t.casefold()))
            ]
            for category, terms in terms_by_category.items()
        }

    def _keywords(self, remarks):
        results = {}
        for category, entries in self.patterns.items():
            found = []
            for term, pattern in entries:
                for match in pattern.finditer(remarks):
                    if _negated(remarks, match.start(), match.end()):
                        continue
                    if not _contextually_valid(category, term, remarks, match.start(), match.end()):
                        continue
                    found.append(_canonical_keyword(category, term))
                    break
            results[category] = list(dict.fromkeys(found))

        def add_if_present(category, label, pattern):
            for match in re.finditer(pattern, remarks, re.I):
                if not _negated(remarks, match.start(), match.end()):
                    results[category].append(_canonical_keyword(category, label))
                    return

        # Common real-estate financing language not necessarily covered by taxonomy.
        add_if_present("financial", "seller_financing_possible", r"\b(?:seller|owner)\s+may\s+finance\b")
        add_if_present("financial", "seller_financing_available", r"\b(?:seller|owner)\s+financing\s+available\b")
        add_if_present("condition", "freshly painted", r"\b(?:fresh(?:ly)?\s+(?:interior\s+)?paint(?:ed)?|new\s+paint)\b")

        # Real-listing phrases observed during Week 6 manual review.
        add_if_present("condition", "needs_repairs", r"\bneeds?\s+(?:(?:some|major|minor)\s+)?repairs?\b")
        add_if_present("condition", "fixer_upper", r"\b(?:fix\s+it\s+up|fixer[\s-]*upper?)\b")
        add_if_present(
            "location", "near_lake",
            r"\b(?:short\s+walk\s+from|walking\s+distance\s+to|steps?\s+from|close\s+to|near)\s+(?:(?:the|a)\s+)?lake\b",
        )

        for category in results:
            results[category] = list(dict.fromkeys(results[category]))
        return results

    def extract_signals(self, listing_record):
        """Extract one listing from a mapping of database column names to values."""
        remarks = _text(listing_record.get("L_Remarks"))
        extracted = self.entity_extractor.extract_all(remarks)
        keywords = self._keywords(remarks)

        db_price = listing_record.get("L_SystemPrice")
        try:
            price = int(db_price) if db_price is not None and int(db_price) > 0 else None
        except (TypeError, ValueError, OverflowError):
            price = None
        if price is None:
            price = extracted.get("price")

        private_db = _boolean(listing_record.get("PoolPrivateYN"))
        pool_features = _pool_feature_tokens(listing_record.get("PoolFeatures"))
        features_explicit_none = pool_features == {"none"}
        feature_community = bool(pool_features & {"community", "association"})
        feature_private = "private" in pool_features
        feature_other = bool(pool_features - {"none", "community", "association"})

        private_text = _pool_text_signal(remarks, r"\bprivate\s+(?:swimming\s+)?pool\b")
        pool_text = _pool_text_signal(remarks, r"\b(?:swimming\s+)?pool\b")
        community_text = _pool_text_signal(
            remarks,
            r"\b(?:community|shared|communal|association)(?:\s+\w+){0,4}\s+(?:swimming\s+)?pool\b"
            r"|\bpool\b.{0,60}\b(?:community|association)\s+amenit"
            r"|\b(?:residents|homeowners|owners)\s+(?:enjoy|have\s+access\s+to|can\s+access)"
            r".{0,180}\b(?:swimming\s+)?pool\b",
        )

        # PoolPrivateYN describes private ownership only. Contradictory explicit
        # private evidence is left unknown; a 0 never rules out community access.
        if private_db is not None:
            if (private_db is False and (private_text is True or feature_private)) or (
                private_db is True and (private_text is False or features_explicit_none)
            ):
                private_pool = None
            else:
                private_pool = private_db
        elif feature_private and private_text is False:
            private_pool = None
        elif feature_private or private_text is True:
            private_pool = True
        elif feature_community or community_text is True:
            private_pool = False
        elif features_explicit_none:
            private_pool = False
        elif pool_text is False:
            private_pool = False
        else:
            private_pool = private_text

        # Explicit community/association tokens and current remarks establish
        # community access. A private-only type or RETS "None" marks it false;
        # generic pool features such as InGround leave access type unknown.
        if feature_community or community_text is True:
            community_pool = True
        elif features_explicit_none or (feature_private and not feature_community):
            community_pool = False
        elif community_text is False or pool_text is False:
            community_pool = False
        else:
            community_pool = None

        # A feature list with a non-None pool type establishes an existing pool.
        # The RETS "None" sentinel is a negative baseline, overridden by explicit
        # current Remarks. Proposed additions and separately paid optional access
        # are not treated as property/community pool amenities.
        if private_pool is True or community_pool is True or feature_private or feature_community or feature_other or pool_text is True:
            has_pool = True
        elif features_explicit_none or pool_text is False:
            has_pool = False
        elif private_pool is False and community_pool is False:
            has_pool = False
        else:
            has_pool = None

        fireplace = _boolean(listing_record.get("FireplaceYN"))
        if fireplace is None:
            fireplace = _feature_signal(remarks, r"\bfireplaces?\b")
        garage = _boolean(listing_record.get("GarageYN"))
        if garage is None:
            garage = _feature_signal(remarks, r"\bgarages?\b")
        view = _boolean(listing_record.get("ViewYN"))
        if view is None and (_available(listing_record.get("View")) or keywords["view"]):
            view = True

        city = listing_record.get("L_City")
        listing_id = listing_record.get("L_ListingID")

        # Week 3 returns mention-level amenities; Week 6 emits unique labels.
        amenities = []
        seen_amenities = set()
        for amenity in extracted.get("amenities") or []:
            label = _canonical_amenity(str(amenity))
            normalized = label
            if normalized and normalized not in seen_amenities:
                seen_amenities.add(normalized)
                amenities.append(label)

        return {
            "listing_id": str(listing_id) if _available(listing_id) else None,
            "entities": {
                "bedrooms": extracted.get("bedrooms"),
                "bathrooms": extracted.get("bathrooms"),
                "sqft": extracted.get("sqft"),
                "price": price,
                "city": _text(city) or None,
            },
            "amenities": amenities,
            "flags": {
                "private_pool": private_pool,
                "community_pool": community_pool,
                "pool": has_pool,
                "fireplace": fireplace,
                "garage": garage,
                "view": view,
            },
            "keywords": keywords,
            "property_condition": _text(listing_record.get("PropertyCondition")) or None,
        }
