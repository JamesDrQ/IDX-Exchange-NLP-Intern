import re
import html
import unicodedata


class TextCleaner:
    def __init__(self):
        self.abbrev_map = {
            # Bedrooms / bathrooms
            "br": "bedroom",
            "bd": "bedroom",
            "bdr": "bedroom",
            "bdrm": "bedroom",
            "ba": "bathroom",
            "bth": "bathroom",
            "bthrm": "bathroom",

            # Rooms
            "mbr": "master bedroom",
            "mba": "master bathroom",
            "lr": "living room",
            "dr": "dining room",
            "fam rm": "family room",
            "kit": "kitchen",
            "kitch": "kitchen",

            # Measurements
            "sqft": "square feet",
            "sq ft": "square feet",
            "sf": "square feet",

            # Common wording
            "w/": "with",
            "w/o": "without",
            "approx": "approximately",
            "incl": "included",
            "excl": "excluded",

            # Property types
            "apt": "apartment",
            "condo": "condominium",

            # Features
            "ac": "air conditioning",
            "a/c": "air conditioning",
            "fp": "fireplace",
            "fpl": "fireplace",
            "gar": "garage",
            "prkg": "parking",
            "pkg": "parking",

            # Time
            "yr": "year",
            "yrs": "years",
            "mo": "month",
            "mos": "months",

            # Real estate
            "hoa": "homeowners association",
            "appt": "appointment",
            "prop": "property",
            "remod": "remodeled",
            "reno": "renovated",
        }

    def normalize_unicode(self, text):
        text = unicodedata.normalize("NFKC", text)

        replacements = {
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "–": "-",
            "—": "-",
            "\xa0": " ",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def remove_html(self, text):
        text = html.unescape(text)
        return re.sub(r"<[^>]+>", " ", text)

    def normalize_prices(self, text):
        # 450k / $450k -> 450000
        text = re.sub(
            r"\$?\s*(\d+(?:\.\d+)?)\s*[kK]\b",
            lambda m: str(int(float(m.group(1)) * 1000)),
            text,
        )

        # 1.2m / $1.2m -> 1200000
        text = re.sub(
            r"\$?\s*(\d+(?:\.\d+)?)\s*[mM]\b",
            lambda m: str(int(float(m.group(1)) * 1_000_000)),
            text,
        )

        # $1,250,000 -> 1250000
        text = re.sub(
            r"\$\s*(\d[\d,]*)",
            lambda m: m.group(1).replace(",", ""),
            text,
        )

        return text

    def normalize_measurements(self, text):
        # 2,000 sqft / 2000 sq ft / 2000 sq. ft.
        return re.sub(
            r"\b([\d,]+)\s*(?:sq\.?\s*ft\.?|sqft)(?!\w)",
            lambda m: f"{m.group(1).replace(',', '')} square feet",
            text,
            flags=re.IGNORECASE,
        )

    def expand_abbreviations(self, text):
        # Longest abbreviations first
        for abbreviation in sorted(
            self.abbrev_map,
            key=len,
            reverse=True,
        ):
            replacement = self.abbrev_map[abbreviation]

            pattern = (
                r"(?<!\w)"
                + re.escape(abbreviation)
                + r"(?!\w)"
            )

            text = re.sub(
                pattern,
                replacement,
                text,
                flags=re.IGNORECASE,
            )

        return text

    def normalize_punctuation(self, text):
        text = re.sub(r"!{2,}", "!", text)
        text = re.sub(r"\?{2,}", "?", text)
        text = re.sub(r"\.{3,}", "...", text)
        return text

    def normalize_whitespace(self, text):
        return re.sub(r"\s+", " ", text).strip()

    def clean_text(self, text):
        if text is None:
            return ""

        text = str(text)

        text = self.normalize_unicode(text)
        text = self.remove_html(text)
        text = self.normalize_prices(text)
        text = self.normalize_measurements(text)
        text = self.expand_abbreviations(text)
        text = self.normalize_punctuation(text)
        text = self.normalize_whitespace(text)

        return text

    def profile_column(self, df, column_name):
        series = df[column_name]
        text_series = series.fillna("").astype(str)

        return {
            "row_count": int(len(series)),
            "null_count": int(series.isnull().sum()),
            "null_rate": float(series.isnull().mean()),
            "avg_length": float(text_series.str.len().mean()),

            "html_count": int(
                text_series.str.contains(
                    r"<[^>]+>",
                    regex=True
                ).sum()
            ),

            "price_k_mentions": int(
                text_series.str.contains(
                    r"\d+(?:\.\d+)?k\b",
                    case=False,
                    regex=True
                ).sum()
            ),

            "price_m_mentions": int(
                text_series.str.contains(
                    r"\d+(?:\.\d+)?m\b",
                    case=False,
                    regex=True
                ).sum()
            ),

            "sqft_mentions": int(
                text_series.str.contains(
                    r"\b(?:sqft|sq\.?\s*ft\.?)\b",
                    case=False,
                    regex=True
                ).sum()
            ),

            "common_terms": self.extract_top_terms(series),
            "common_abbreviations": self.detect_abbreviations(series),
        }

    def detect_abbreviations(self, series):
        text = " ".join(series.fillna("").astype(str)).lower()

        counts = {}

        for abbr in self.abbrev_map:
            pattern = r"(?<!\w)" + re.escape(abbr) + r"(?!\w)"
            matches = re.findall(pattern, text, flags=re.IGNORECASE)

            if matches:
                counts[abbr] = len(matches)

        return dict(
            sorted(
                counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
        )

    
    def extract_top_terms(self, series, top_n=20):
        text = " ".join(series.fillna("").astype(str)).lower()

        words = re.findall(r"\b[a-z]{3,}\b", text)

        stopwords = {
            "the", "and", "for", "with", "this", "that",
            "from", "are", "you", "your", "has", "have",
            "into", "its", "was", "but", "not", "all",
            "can", "will", "our", "out", "off"
        }

        words = [
            word for word in words
            if word not in stopwords
        ]

        from collections import Counter
        return dict(Counter(words).most_common(top_n))