import pandas as pd
import nltk

from collections import Counter
from nltk.util import ngrams
from nltk.corpus import stopwords

df = pd.read_csv("data/processed/listing_sample.csv")

all_text = " ".join(
    df["remarks"]
    .dropna()
    .astype(str)
    .str.lower()
)

stop_words = set(stopwords.words("english"))

tokens = [
    token
    for token in nltk.word_tokenize(all_text)
    if token.isalpha()
]

rows = []

for n in [1, 2, 3]:
    grams = ngrams(tokens, n)
    freq = Counter(grams)

    limit = 500

    for gram, count in freq.most_common(limit):
        # At least contain one non-stopword.
        if all(word in stop_words for word in gram):
            continue

        rows.append({
            "term": " ".join(gram),
            "ngram": n,
            "count": count
        })

candidates = pd.DataFrame(rows)

candidates.to_csv(
    "data/processed/taxonomy_candidates.csv",
    index=False
)

print("Saved", len(candidates), "candidate terms")
print(candidates.head(80))