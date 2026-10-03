import os
import sys
import pandas as pd
import pytest

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from scripts.text_cleaning import TextCleaner


@pytest.fixture
def cleaner():
    return TextCleaner()


# -------------------------
# Price normalization
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("450k", "450000"),
        ("$450k", "450000"),
        ("750K", "750000"),
        ("1.2m", "1200000"),
        ("$1.2m", "1200000"),
        ("2M", "2000000"),
        ("$1,250,000", "1250000"),
    ],
)
def test_price_normalization(cleaner, input_text, expected):
    assert cleaner.normalize_prices(input_text) == expected


# -------------------------
# Measurement normalization
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("2000 sqft", "2000 square feet"),
        ("2,000 sqft", "2000 square feet"),
        ("1500 sq ft", "1500 square feet"),
        ("1500 sq. ft.", "1500 square feet"),
        ("800 SQFT", "800 square feet"),
    ],
)
def test_measurement_normalization(cleaner, input_text, expected):
    assert cleaner.normalize_measurements(input_text) == expected


# -------------------------
# Unicode normalization
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("Seller’s home", "Seller's home"),
        ("“Beautiful home”", '"Beautiful home"'),
        ("Large—home", "Large-home"),
        ("Open–concept", "Open-concept"),
        ("home\xa0with pool", "home with pool"),
    ],
)
def test_unicode_normalization(cleaner, input_text, expected):
    assert cleaner.normalize_unicode(input_text) == expected


# -------------------------
# HTML removal
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("<b>Beautiful</b>", " Beautiful "),
        ("<p>Pool home</p>", " Pool home "),
        ("Home<br>with pool", "Home with pool"),
        ("<div>Luxury</div>", " Luxury "),
    ],
)
def test_html_removal(cleaner, input_text, expected):
    assert cleaner.remove_html(input_text) == expected


# -------------------------
# Abbreviation expansion
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("3 br home", "3 bedroom home"),
        ("2 ba home", "2 bathroom home"),
        ("HOA fee", "homeowners association fee"),
        ("home w/ pool", "home with pool"),
        ("home w/o garage", "home without garage"),
        ("1200 sqft", "1200 square feet"),
        ("1200 sq ft", "1200 square feet"),
        ("approx value", "approximately value"),
        ("condo unit", "condominium unit"),
        ("mbr upstairs", "master bedroom upstairs"),
    ],
)
def test_abbreviation_expansion(cleaner, input_text, expected):
    assert cleaner.expand_abbreviations(input_text) == expected


# -------------------------
# Whitespace normalization
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("hello   world", "hello world"),
        (" hello world ", "hello world"),
        ("hello\nworld", "hello world"),
        ("hello\tworld", "hello world"),
    ],
)
def test_whitespace_normalization(cleaner, input_text, expected):
    assert cleaner.normalize_whitespace(input_text) == expected


# -------------------------
# Punctuation normalization
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("Amazing!!!", "Amazing!"),
        ("Really???", "Really?"),
        ("Great......", "Great..."),
    ],
)
def test_punctuation_normalization(cleaner, input_text, expected):
    assert cleaner.normalize_punctuation(input_text) == expected


# -------------------------
# Full pipeline
# -------------------------

@pytest.mark.parametrize(
    "input_text, expected_parts",
    [
        (
            "<b>Beautiful 3 BR home</b> for $450k",
            ["Beautiful", "3 bedroom", "450000"],
        ),
        (
            "2 BA condo w/ 2,000 sqft",
            ["2 bathroom", "condominium", "with", "2000 square feet"],
        ),
        (
            "“Luxury” home — approx $1.2m",
            ['"Luxury"', "approximately", "1200000"],
        ),
    ],
)
def test_full_cleaning_pipeline(cleaner, input_text, expected_parts):
    result = cleaner.clean_text(input_text)

    for expected in expected_parts:
        assert expected in result


# -------------------------
# Profiling
# -------------------------

def test_profile_column(cleaner):
    df = pd.DataFrame(
        {
            "remarks": [
                "Beautiful 3 br home with 1200 sqft",
                "HOA community",
                None,
            ]
        }
    )

    profile = cleaner.profile_column(df, "remarks")

    assert profile["row_count"] == 3
    assert profile["null_count"] == 1
    assert "null_rate" in profile
    assert "avg_length" in profile
    assert "common_terms" in profile
    assert "common_abbreviations" in profile


def test_detect_abbreviations(cleaner):
    series = pd.Series(
        [
            "3 br 2 ba home",
            "HOA community",
            "home w/ pool",
        ]
    )

    result = cleaner.detect_abbreviations(series)

    assert result["br"] == 1
    assert result["ba"] == 1
    assert result["hoa"] == 1
    assert result["w/"] == 1