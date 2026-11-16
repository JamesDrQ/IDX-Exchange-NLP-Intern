"""Regex and Week 1 taxonomy based entity extraction for Week 3 listings.

The span API is used by annotation_helper and the interactive annotator. The
value API remains available for callers that only need structured values.
"""

import json
from functools import lru_cache
from pathlib import Path
import re


NUMBER_WORDS = (
    "zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    "eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    "eighteen|nineteen|twenty"
)
QUANTITY = (
    rf"(?:\d+(?:\.\d+)?|\d+\s+\d/\d|\d/\d|"
    rf"(?:{NUMBER_WORDS})(?:[- ]and[- ]a?[- ]half)?|"
    rf"(?:{NUMBER_WORDS})[- ](?:{NUMBER_WORDS}))"
)

BEDROOM_RE = re.compile(
    rf"\b{QUANTITY}\s*[- ]?(?:(?:additional|spacious|cozy|secondary|large)\s+|"
    rf"generously\s+sized\s+)?(?:secondary\s+)?(?:bedrooms?|beds?|br|bd)\b", re.I
)
BATHROOM_RE = re.compile(
    rf"\b{QUANTITY}\s*[- ]?(?:full|half|three-quarter|three quarter)?\s*"
    rf"(?:bathrooms?|baths?|ba)\b", re.I
)
SQFT_RE = re.compile(
    r"\b(?:\d{1,3}(?:,\d{3})+|\d+)\s*(?:square\s+f(?:ee|oo)t|sq\.?\s*ft\.?|sqft)\b",
    re.I,
)

# A plain amount is only a price when listing language or a dollar sign gives
# it a property-price context. Finance, income, HOA, and reduction amounts are
# deliberately excluded.
_AMOUNT = r"\$?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:\s*(?:k|m|million|thousand))?"
PRICE_CONTEXT_RE = re.compile(
    rf"\b(?:offered(?:\s+from)?|asking\s+price|listing\s+price|"
    rf"listed\s+at|priced\s+at|price\s+of|sale\s+price(?:\s+of)?|"
    rf"sold\s+for)\s*:?[ ]*({_AMOUNT})",
    re.I,
)
PRICE_RANGE_RE = re.compile(
    rf"\b(?:offered(?:\s+from)?|priced\s+from|price\s+range\s+of)\s*:?[ ]*"
    rf"({_AMOUNT})\s+(?:to|[-–])\s+({_AMOUNT})",
    re.I,
)
DOLLAR_AMOUNT_RE = re.compile(
    r"\$\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:k|m|million|thousand)?\b",
    re.I,
)
PRICE_EXCLUSION_RE = re.compile(
    r"\b(?:grant|financ(?:e|ing|ed)|loan|income|salary|hoa|association fee|"
    r"monthly payment|lease|reduced|reduction|price improvement|closing costs?)\b",
    re.I,
)


class EntityExtractor:
    """Extract exact Week 3 entity spans from listing remarks."""

    labels = {"BEDROOM", "BATHROOM", "SQFT", "PRICE", "AMENITY"}
    _excluded_taxonomy_terms = {
        "floor plan",
        "open floor plan",
        "living space",
        "outdoor space",
        "outdoor living",
        "pool and spa",
        "nearby",
        "walking distance",
        "minutes from",
        "just minutes",
        "located near",
        "close to shopping",
        "near shopping",
        "easy access",
        "convenient access",
        "conveniently located",
        "school district",
        "schools",
        "parks",
        "restaurants",
        "beach",
        "concierge",
        "income",
        "rental",
    }

    # Qualifiers that can make a Week 1 feature term a more meaningful span.
    # Expansion is limited to this list to avoid absorbing promotional prose.
    _feature_modifiers = {
        "abundant", "attached", "brand-new", "brick", "built-in", "covered",
        "custom", "custom-built", "detached", "dual-pane", "enclosed", "expansive",
        "fenced", "finished", "granite", "large", "mature", "oversized",
        "private", "quartz", "recessed", "renovated", "saltwater", "sparkling",
        "stainless-steel", "updated", "vaulted", "walk-in", "waterfall",
        "wood-burning", "wood-style", "wood-look",
    }

    # Useful development-split misses absent from the Week 1 taxonomy.
    _development_terms = {
        "artificial turf", "back yard", "breakfast bar", "built-in microwave",
        "cabanas", "california room", "carpet", "city-scape views",
        "covered deck", "large windows", "garden level", "covered entertaining areas", "covered porch",
        "dual vanities", "fire pit", "gas stove", "guest parking", "6 person spa",
        "hillside views", "jetted tub", "new flooring", "new hvac system",
        "newer front door", "newer roof", "newer windows", "outdoor grill",
        "outdoor kitchen", "outdoor storage room", "panoramic pauma valley views",
        "paver patios", "private driveway", "private pool", "privacy fence",
        "promenade", "rose gardens", "screened patio", "sparkling swimming pool",
        "stone fireplace", "stone flooring", "vaulted beamed ceilings",
        "walk-in closet", "walk-in closets", "walk-in pantry", "walk-in shower", "washer and dryer",
        "wood-style flooring", "dual-pane windows", "finished garage",
        "detached finished garage", "secure garage", "large shed", "pavilion",
        "gardening space", "refrigerator", "dishwasher", "quartz countertop",
        "primary retreat", "bonus loft area", "two-car garage", "1 car garage",
        "2 car direct access garage", "first floor suite", "interior doors",
        "granite art corner display shelves", "frosted back panels",
        "standing wardrobes", "smart home automation technology hub",
        "private ev charger", "assigned 2 car parking", "18+ ft ceilings",
        "rooftop pool", "primary bathroom", "separate entrance", "bedroom/office",
        "grilling", "spas", "ensuite bath", "assigned covered parking space",
        "24-hour security",
    }

    def __init__(self):
        self._taxonomy_terms = self.load_taxonomy()

    @staticmethod
    def _quantity_value(value):
        value = value.casefold().strip().replace("-", " ")
        fraction = re.match(r"^(\d+)\s+(\d+)/(\d+)", value)
        if fraction:
            return float(fraction.group(1)) + int(fraction.group(2)) / int(fraction.group(3))
        number = re.match(r"^\d+(?:\.\d+)?", value)
        if number:
            parsed = float(number.group())
            return int(parsed) if parsed.is_integer() else parsed
        words = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
            "fourteen": 14, "fifteen": 15, "sixteen": 16,
            "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        }
        tokens = value.split()
        if tokens and tokens[0] in words:
            result = words[tokens[0]]
            if "half" in tokens:
                result += 0.5
            elif len(tokens) > 1 and tokens[1] in words:
                result += words[tokens[1]]
            return int(result) if float(result).is_integer() else result
        return None

    @staticmethod
    def _price_value(value):
        normalized = value.casefold().replace("$", "").replace(",", "").strip()
        multiplier = 1
        for suffix, scale in (("million", 1_000_000), ("thousand", 1_000), ("m", 1_000_000), ("k", 1_000)):
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
                multiplier = scale
                break
        result = float(normalized) * multiplier
        return int(result) if result.is_integer() else result

    @staticmethod
    @lru_cache(maxsize=1)
    def load_taxonomy():
        taxonomy_path = (
            Path(__file__).resolve().parent.parent
            / "data/processed/taxonomy.json"
        )
        with taxonomy_path.open("r", encoding="utf-8") as f:
            taxonomy = json.load(f)

        categories = {"amenity", "interior_feature", "exterior_feature", "view"}
        terms = []
        for item in taxonomy["terms"]:
            term = item["term"].strip()
            if item["category"] not in categories:
                continue
            if term.casefold() in EntityExtractor._excluded_taxonomy_terms:
                continue
            # Generic view words are too underspecified to label on their own.
            if item["category"] == "view" and term.casefold() in {"view", "views", "panoramic"}:
                continue
            terms.append(term)
        # Longest first ensures a phrase such as "private balcony" wins over
        # its embedded "balcony" term during overlap resolution.
        terms.extend(EntityExtractor._development_terms)
        return tuple(sorted(set(terms), key=lambda term: (-len(term), term.casefold())))

    def _amenity_spans(self, text):
        found = []
        for term in self._taxonomy_terms:
            body = r"[\s\u2010-\u2015-]+".join(
                re.escape(piece) for piece in re.split(r"\s+", term.strip()) if piece
            )
            pattern = re.compile(r"(?<!\w)" + body + r"(?!\w)", re.I)
            for match in pattern.finditer(text):
                start, end = match.span()

                # A nearby public facility is not an amenity of the property.
                prefix = text[max(0, start - 64):start]
                if re.search(
                    r"\b(?:walking distance to|steps from|near(?:by)?|"
                    r"minutes? from|close to|across (?:the )?street from)\s+[^.!?;]*$",
                    prefix,
                    re.I,
                ):
                    continue

                # A bare mention of doors is often incidental copy ("front
                # door", "double doors"). Keep it only when the phrase names
                # a recognizable door feature; specific taxonomy terms such as
                # French doors are independently matched below.
                if term.casefold() == "doors":
                    preceding = text[max(0, start - 24):start]
                    if not re.search(
                        r"\b(?:french|sliding|glass|pocket|patio|interior|exterior|"
                        r"double|folding|barn)\s+$", preceding, re.I,
                    ):
                        continue

                # Some taxonomy entries are bare nouns. Add only an immediately
                # adjacent known modifier, preserving the shortest useful span.
                left = text[max(0, start - 40):start]
                modifiers = list(re.finditer(r"\s+([\w-]+)(?:,\s*)?$", left))
                if modifiers:
                    modifier = modifiers[-1]
                    token = modifier.group(1).casefold()
                    if token in self._feature_modifiers:
                        start -= len(modifier.group())
                        start += len(modifier.group()) - len(modifier.group().lstrip())

                found.append((start, end, "AMENITY"))
        return found

    @staticmethod
    def _price_spans(text):
        spans = []
        for match in PRICE_RANGE_RE.finditer(text):
            for group in (1, 2):
                start, end = match.span(group)
                while end > start and text[end - 1].isspace():
                    end -= 1
                spans.append((start, end, "PRICE"))

        for match in PRICE_CONTEXT_RE.finditer(text):
            amount = match.group(1)
            start, end = match.span(1)
            # Do not reinterpret a stated discount/financing amount as price.
            context_start = max(
                text.rfind(mark, 0, match.start()) for mark in ".!?;\n"
            ) + 1
            context = text[context_start:min(len(text), match.end() + 40)]
            if not PRICE_EXCLUSION_RE.search(context):
                while end > start and text[end - 1].isspace():
                    end -= 1
                spans.append((start, end, "PRICE"))

        for match in DOLLAR_AMOUNT_RE.finditer(text):
            context_start = max(
                text.rfind(mark, 0, match.start()) for mark in ".!?;,\n"
            ) + 1
            context = text[context_start:min(len(text), match.end() + 40)]
            if PRICE_EXCLUSION_RE.search(context):
                continue
            # Avoid duplicate spans already detected with explicit price wording.
            if not any(start < match.end() and end > match.start() for start, end, _ in spans):
                spans.append((*match.span(), "PRICE"))
        return spans

    def extract_spans(self, text):
        """Return non-overlapping [start, end, label] spans for every match."""
        if not isinstance(text, str):
            return []
        candidates = []
        for pattern, label in (
            (BEDROOM_RE, "BEDROOM"),
            (BATHROOM_RE, "BATHROOM"),
            (SQFT_RE, "SQFT"),
        ):
            candidates.extend((m.start(), m.end(), label) for m in pattern.finditer(text))
        candidates.extend(self._price_spans(text))
        candidates.extend(self._amenity_spans(text))

        # Prefer the most specific span when the Week 1 taxonomy contains both
        # a phrase and one of its component terms.
        candidates.sort(key=lambda x: (-(x[1] - x[0]), x[0], x[2]))
        selected = []
        for candidate in candidates:
            start, end, _ = candidate
            if not any(start < prior[1] and end > prior[0] for prior in selected):
                selected.append(candidate)
        return [list(x) for x in sorted(selected, key=lambda x: (x[0], x[1], x[2]))]

    def extract_bedrooms(self, text):
        match = BEDROOM_RE.search(text or "")
        return self._quantity_value(match.group(0)) if match else None

    def extract_bathrooms(self, text):
        match = BATHROOM_RE.search(text or "")
        value = self._quantity_value(match.group(0)) if match else None
        return float(value) if value is not None else None

    def extract_sqft(self, text):
        match = SQFT_RE.search(text or "")
        number = re.match(r"[\d,]+", match.group(0)) if match else None
        return int(number.group().replace(",", "")) if number else None

    def extract_price(self, text):
        spans = self._price_spans(text or "")
        if not spans:
            return None
        start, end, _ = spans[0]
        return self._price_value(text[start:end])

    def extract_amenities(self, text):
        return [text[start:end] for start, end, label in self._amenity_spans(text or "")]

    def extract_all(self, text):
        spans = self.extract_spans(text)
        result = {"bedrooms": None, "bathrooms": None, "price": None, "sqft": None, "amenities": []}
        for start, end, label in spans:
            value = text[start:end]
            key = {"BEDROOM": "bedrooms", "BATHROOM": "bathrooms", "SQFT": "sqft", "PRICE": "price"}.get(label)
            if key and result[key] is None:
                if label == "BEDROOM":
                    result[key] = self._quantity_value(value)
                elif label == "BATHROOM":
                    parsed = self._quantity_value(value)
                    result[key] = float(parsed) if parsed is not None else None
                elif label == "SQFT":
                    result[key] = int(re.match(r"[\d,]+", value).group().replace(",", ""))
                else:
                    result[key] = self._price_value(value)
            elif label == "AMENITY":
                result["amenities"].append(value)
        return result
