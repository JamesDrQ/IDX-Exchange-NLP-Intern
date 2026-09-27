import json
import pandas as pd


def test_taxonomy_loaded():
    with open("data/processed/taxonomy.json") as f:
        tax = json.load(f)

    assert "terms" in tax
    assert len(tax["terms"]) >= 200

    assert all(
        "id" in t
        and "term" in t
        and "category" in t
        for t in tax["terms"]
    )


def test_taxonomy_categories():
    with open("data/processed/taxonomy.json") as f:
        tax = json.load(f)

    categories = {
        t["category"]
        for t in tax["terms"]
    }

    assert len(categories) == 8


def test_sample_data_quality():
    df = pd.read_csv("data/processed/listing_sample.csv")

    assert len(df) >= 500
    assert df["remarks"].str.len().min() > 50

def test_sample_queries():
    df = pd.read_csv("data/processed/sample_queries.csv")

    assert len(df) >= 50
    assert df["query"].notna().all()
    assert df["intent"].notna().all()

def test_taxonomy_coverage():
    import json
    import pandas as pd

    with open("data/processed/taxonomy.json") as f:
        tax = json.load(f)

    terms = [
        t["term"].lower()
        for t in tax["terms"]
    ]

    df = pd.read_csv("data/processed/listing_sample.csv")

    def has_taxonomy_term(text):
        text = str(text).lower()
        return any(term in text for term in terms)

    coverage = df["remarks"].apply(has_taxonomy_term).mean()

    print(f"Taxonomy coverage: {coverage:.2%}")

    assert coverage >= 0.30